# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2020 Miklas Riechmann

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
This module interfaces saved events on the disk to the remainder of the event filtering pipeline. It is intended that event directories are read in as a queue from :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk` and loaded into memory in turn by :class:`~DynAIkonTrap.filtering.remember_from_disk.EventRememberer`. 

Events are loaded with into instances of :class:`~DynAIkonTrap.filtering.remember_from_disk.EventData`.

The output is accessible via a queue. 
"""
from ctypes import Union
from dataclasses import dataclass, field
from distutils.file_util import copy_file
from os import nice
from os.path import join
from shutil import copyfile
from multiprocessing import Array, Process, Queue
from multiprocessing.queues import Queue as QueueType
from pathlib import Path
from queue import Empty
from time import time
from typing import List, Union
from os import path
import numpy as np

from DynAIkonTrap.camera_to_disk import CameraToDisk, MotionRAMBuffer, DirectoryMaker
from DynAIkonTrap.imdecode import YUV_BYTE_PER_PIX, decoder
from DynAIkonTrap.logging import get_logger

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from vid2frames.Vid2Frames import VideoStream

logger = get_logger(__name__)


@dataclass
class EventData:
    """A class for storing motion event data for further processing."""
    raw_raster_file_indices: List[int] = field(default_factory=list)
    dir: str = ""
    start_timestamp: float = 0.0

class EventSynthesisor:
    """This object reads events from a VideoStream and creates synthetic EventData packages. Produces event directories upon calling of the contained get() method."""
    def __init__(self, read_from: "VideoStream", video_path: str):
        """Initialise an event Sythesisor from a Vid2Frames.VideoStream. 

        Args:
            read_from (VideoStream): The VideoStream to read each frame from. This is used to capture the raw image frames in YUV format
            video_path (str): The video file from which the VideoStream is generated from. Used to copy an encoded video to the event directory
        """
        self._input_queue: "VideoStream" = read_from
        self.raw_dims = (0,0)
        self.framerate = read_from.framerate
        self._output_queue: QueueType[EventData]
        self._dir_maker = DirectoryMaker('output/vid2frames')
        self._video_path: str = video_path
    
    def get(self) -> str:
        """Produces an event directory from the given VideoStream used for initialisation. 
        
        YUV format image frames are interpreted and read from each image frame and saved to `clip.dat`

        An encoded video file is copied to the output directory and named `clip.mp4`

        Returns:
            str: Directory for the synthesised event, containing `clip.mp4` and `clip.dat`
        """
        event_dir = self._dir_maker.new_event()
        frame = self._input_queue.get() #block until frame is available
        logger.info("Parsing `{}` into an event. Saving to {}; this may take a few seconds.".format(self._video_path, event_dir))
        encoded_path = event_dir + '/clip.mp4'
        copy_file(self._video_path, encoded_path)
        raw_path =  event_dir + '/clip.dat'
        while True:
            try:
                bgr = decoder.jpg_buf_to_bgr_array(frame.image)
                yuv_buf = decoder.bgr_array_to_yuv_buf(bgr)
                with open(raw_path, 'ab') as f:
                    f.write(yuv_buf)
                frame = self._input_queue.get()
            except Empty:
                break
        return event_dir
            

class EventRememberer:
    """This object reads new event directories from an instance of :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk`. Outputs a Queue of EventData objects for further processing."""

    def __init__(self, read_from: Union[CameraToDisk, EventSynthesisor]):
        """Initialises EventRememberer. Starts events processing thread.

        Args:
            read_from (CameraToDisk): The :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk` object creating event directories on disk.
        """
        self._output_queue: QueueType[EventData] = Queue(maxsize=20)
        self._input_queue = read_from
        self.framerate = read_from.framerate

        self._usher = Process(target=self.proc_events, daemon=True)
        self._usher.start()

    def proc_events(self):
        """Process input queue of event directories"""
        nice(4)
        while True:
            try:
                event_dir = self._input_queue.get()
                self._output_queue.put(self.dir_to_event(event_dir))
            except Empty:
                logger.error("Trying to read from empty event directory queue")
                pass

    def dir_to_event(self, dir: str) -> EventData:
        """converts an event directory to an instance of EventData

        Args:
            dir (str): event directory

        Returns:
            EventData: populated instance of event data.
        """
        raw_path = join(dir, "clip.dat")
        raw_raster_frame_indices = []
        try:
            with open(raw_path, 'rb') as f:
                b = f.read(4)
                while(b != b''):
                    raw_raster_frame_indices.append(f.tell() - 4)
                    frame_height, frame_width = tuple(np.frombuffer(b, dtype=np.uint16))
                    f.read(int(int(frame_width) * int(frame_height) * YUV_BYTE_PER_PIX))
                    b = f.read(4)
        except IOError as e:
            logger.error(
                "Problem opening or reading file: {} (IOError: {})".format(raw_path, e))
        
        return EventData(
            raw_raster_file_indices=raw_raster_frame_indices,
            dir=dir,
            start_timestamp=time()
        )

    def get(self) -> EventData:
        """Get next EventData object in the output queue

        Returns:
            EventData: Next EventData object
        """
        return self._output_queue.get()
