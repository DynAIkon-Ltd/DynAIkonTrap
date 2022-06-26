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
from dataclasses import dataclass
from os import nice
from multiprocessing import Array, Process, Queue
from multiprocessing.queues import Queue as QueueType
from pathlib import Path
from struct import unpack
from queue import Empty
from time import time
from typing import List
from io import open
from os import path

from DynAIkonTrap.camera_to_disk import CameraToDisk, MotionRAMBuffer
from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EventData:
    """A class for storing motion event data for further processing."""
    raw_raster_file_indices: List[int]
    raw_raster_path: str
    dir: str
    start_timestamp: float
    raw_x_dim: int
    raw_y_dim: int
    raw_bpp: int


class EventRememberer:
    """This object reads new event directories from an instance of :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk`. Outputs a Queue of EventData objects for further processing."""

    def __init__(self, read_from: CameraToDisk):
        """Initialises EventRememberer. Starts events processing thread.

        Args:
            read_from (CameraToDisk): The :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk` object creating event directories on disk.
        """
        self._output_queue: QueueType[EventData] = Queue(maxsize=1)
        self._input_queue = read_from
        self.raw_dims = read_from.raw_frame_dims
        self.raw_bpp = 1.5
        self.framerate = read_from.framerate
        width, height = read_from.resolution

        self._rows, self._cols = MotionRAMBuffer.calc_rows_cols(width, height)
        self._motion_element_size = MotionRAMBuffer.calc_motion_element_size(
            self._rows, self._cols
        )

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
        raw_path = Path(dir).joinpath("clip.dat")
        vect_path = Path(dir).joinpath("clip_vect.dat")
        raw_raster_frames = []
        raw_raster_file_indices = []
        try:
            file_size = path.getsize(raw_path)
            file_indx = 0
            while file_indx < file_size:
                raw_raster_file_indices.append(int(file_indx))
                file_indx += (self.raw_dims[0] * self.raw_dims[1] * self.raw_bpp)
        except OSError as e:
            logger.error(
                "Problem opening or reading file: {} (IOError: {})".format(e.filename, e))
        
        return EventData(
            raw_raster_file_indices=raw_raster_file_indices,
            raw_raster_path=raw_path,
            dir=dir,
            start_timestamp=time(),  # set event time set to now
            raw_x_dim=self.raw_dims[0],
            raw_y_dim=self.raw_dims[1],
            raw_bpp=self.raw_bpp,
        )

    def get(self) -> EventData:
        """Get next EventData object in the output queue

        Returns:
            EventData: Next EventData object
        """
        return self._output_queue.get()
