# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2021 Ross Gardiner

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
This module handles detection and recording of motion events to disk. This interfaces with :class:`~DynAIkonTrap.custom_picamera.DynCamera` to buffer streams of vectors, H264 data and a raw stream. 

Motion detection is performed within :class:`MotionRAMBuffer` by filtering each motion vectors for each frame using :class:`~DynAIkonTrap.filtering.motion.MotionFilter`. When motion is detected, the buffers are emptied to a location on disk for further processing. 

An output queue of emptied buffer directories is accessible via the output of :class:`CameraToDisk`. 
"""
from queue import Empty
from pathlib import Path
from math import ceil
from time import time
import psutil
from multiprocessing import Queue
from multiprocessing.queues import Queue as QueueType
from typing import Tuple
from threading import Thread

try:
    from picamera import PiCamera

except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass

from DynAIkonTrap.video_buffers import MotionRAMBuffer, H264RAMBuffer, RawRAMBuffer, BUFF_SZ_S, BITRATE
from DynAIkonTrap.filtering.animal import NetworkInputSizes
from DynAIkonTrap.imdecode import YUV_BYTE_PER_PIX
from DynAIkonTrap.settings import (
    CameraSettings,
    FilterSettings,
    WriterSettings,
)
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)

class DirectoryMaker:
    """Creates new directories for storing motion events."""

    def __init__(self, base_dir: Path):
        """Takes a base Path object and initialises a directory factory for motion events.

        Args:
            base_dir (Path): base directory for storing motion event folders.
        """
        self._base_dir = base_dir
        self._event_counter = 0

    def get_event(self) -> Tuple[Path, str]:
        """Searches for a new directory path for motion event until an unoccupied one is found


        Returns:
            Tuple[Path, str]: Event directory
        """

        ret_path, ret_str = self.new_event()
        while ret_path.exists():
            ret_path, ret_str = self.new_event()
        ret_path.mkdir(parents=True, exist_ok=True)
        return (ret_path, ret_str)

    def new_event(self) -> Tuple[Path, str]:
        """Gives string name and directory path for a new motion event on disk"""

        ret_str = "event_" + str(self._event_counter)
        self._event_counter += 1
        ret_path = self._base_dir.joinpath(ret_str)
        return (ret_path, ret_str)


class CameraToDisk:
    """Wraps :class:`~DynAIkonTrap.custom_picamera.DynCamera` functionality to stream motion events to disk."""

    def __init__(
        self,
        camera_settings: CameraSettings,
        writer_settings: WriterSettings,
        filter_settings: FilterSettings,
    ):
        """Initialiser, creates instance of camera and buffers for catching it's output.

        Args:
            camera_settings (CameraSettings): settings object for camera construction
            writer_settings (WriterSettings): settings object for writing out events
            filter_settings (FilterSettings): settings object for filter parameters
        """
        self.resolution = camera_settings.resolution
        
        if (
            filter_settings.animal.detect_humans
            or filter_settings.animal.fast_animal_detect
        ):
            self.raw_frame_dims = NetworkInputSizes.SSDLITE_MOBILENET_V2
        else:
            self.raw_frame_dims = NetworkInputSizes.YOLOv4_TINY
        # picamera requires resize dims to be a multiple of 32, for now, we have to resize to this.
        # in the future, re-train a network with appropriate input dims, to-do
        factor_32 = tuple(map(lambda x: ceil(x / 32.0), self.raw_frame_dims))
        self.raw_frame_dims = tuple(map(lambda x: int(x * 32), factor_32))
        self.framerate = camera_settings.framerate
        self._camera =  PiCamera(
            resolution=camera_settings.resolution,
            framerate=camera_settings.framerate,
        )

        self._on = True
        self._context_length_s = filter_settings.processing.context_length_s

        self._maximum_event_length_s: float = (
            filter_settings.processing.max_sequence_period_s
        )

        self._output_queue: QueueType[str] = Queue()
        self._h264_buffer: H264RAMBuffer = H264RAMBuffer(
            filter_settings.processing.context_length_s,
            self._camera,
            splitter_port=1
        )
        self._raw_buffer: RawRAMBuffer = RawRAMBuffer(
            filter_settings.processing.context_length_s,
            self._camera,
            splitter_port=2,
            dim=self.raw_frame_dims,
        )

        self._motion_buffer: MotionRAMBuffer = MotionRAMBuffer(
            self._camera,
            filter_settings.motion,
            filter_settings.processing.context_length_s,
        )

        self._directory_maker: DirectoryMaker = DirectoryMaker(
            Path(writer_settings.path)
        )
        self._record_proc = Thread(
            target=self.record, name="camera recording process", daemon=True
        )
        self._record_proc.start()

    def record(self):
        """Function records streams from the camera to RAM buffers. When motion is detected, buffers are emptied in three stages. 1) motion occurs, initial buffers are emptied to fill context time. Here an event is started on disk. 2) while motion continues and the length of the event is smaller than the max. event length continue writing to disk and swapping buffers as they become full. 3) motion has ended, continue recording for a trail-off period equal to the context length. Finally switch buffers and empty one last time.

        When a motion event finishes, it's saved directory is added to the output queue.
        """
        p = psutil.Process()
        p.ionice(psutil.IOPRIO_CLASS_BE, 0)
        current_path = self._directory_maker.get_event()[0]
        event_io_latencies = []
        self._camera.start_recording(
            self._h264_buffer,
            format="h264",
            splitter_port=1,
            motion_output=self._motion_buffer,
            bitrate=BITRATE,
            intra_period=int((self._context_length_s / 2) * self.framerate),
        )
        self._camera.start_recording(
            self._raw_buffer,
            format='yuv',
            splitter_port=2,
            resize=self.raw_frame_dims,
        )
        self._camera.wait_recording(5)  # camera warm-up
        try:
            while self._on:
                self._camera.wait_recording(1)
                if self._motion_buffer.is_motion:  # motion is detected!
                    logger.info("Motion detected, emptying buffers to disk.")
                    event_dir = current_path
                    motion_start_time = time()
                    last_buffer_empty_t = time()
                    self.empty_all_buffers(current_path, start=True)
                    event_io_latencies.append(time() - last_buffer_empty_t)

                    # continue writing to buffers while motion and the max event length is not reached
                    while (
                        self._motion_buffer.is_motion
                        and (time() - motion_start_time) < self._maximum_event_length_s
                    ):
                        # check if buffers are getting near-full, to keep all three buffers in sync this is done by simply checking the time.
                        if (time() - last_buffer_empty_t) > (0.75 * BUFF_SZ_S):
                            last_buffer_empty_t = time()
                            self.empty_all_buffers(current_path, start=False)
                            event_io_latencies.append(time() - last_buffer_empty_t)
                        self._camera.wait_recording(0.2)
                    #motion finished, notify the user
                    logger.info(
                        "Motion ended, total event length (excluding context time) {:.2f}secs".format(
                            time() - motion_start_time
                        )
                    )
                    # motion finished, wait for context period
                    self._camera.wait_recording(self._context_length_s)
                    
                    # empty buffers, record how long that took!
                    last_buffer_empty_t = time()
                    self.empty_all_buffers(current_path, start=False)
                    t = time() - last_buffer_empty_t
                    event_io_latencies.append(time() - last_buffer_empty_t) 

                    self._output_queue.put(event_dir)
                    
                    logger.debug(
                        "Average time for motion computation over the event: {:.6f}secs".format(
                            self._motion_buffer.get_avg_motion_compute_time()
                        )
                    )
                    logger.debug(
                        "Average IO access latency for {} buffer empties over the event: {:.4f}secs".format(len(event_io_latencies),
                            (sum(event_io_latencies)/len(event_io_latencies))
                        )
                    )
                    current_path = self._directory_maker.get_event()[0]
                    event_io_latencies = []

        finally:
            self._camera.stop_recording()

    def get(self) -> str:
        try:
            return self._output_queue.get()

        except Empty:
            logger.error("No events available from Camera")
            raise Empty

    def empty_all_buffers(self, current_path: Path, start: bool):
        """Switches and empties all three buffers. Switching is performed near-simultaneously. Writing may take longer.

        Args:
            current_path (Path): directory to write events
            start (bool): True if start of a new motion event, False otherwise.
        """
        # switch all buffers first
        self._h264_buffer.switch_stream()
        self._raw_buffer.switch_stream()
        self._motion_buffer.switch_stream()

        self._h264_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip.h264"), is_start=start
        )
        self._raw_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip.dat"), is_start=start
        )
        self._motion_buffer.write_inactive_stream(
            filename=current_path.joinpath("clip_vect.dat"), is_start=start
        )
