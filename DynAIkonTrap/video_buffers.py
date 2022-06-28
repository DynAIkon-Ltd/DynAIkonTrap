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
This file contains definitions for video buffers on RAM which hold circular streams of motion vectors, H264 data and raw image format. 

Motion detection is performed within :class:`MotionRAMBuffer` by filtering each motion vectors for each frame using :class:`~DynAIkonTrap.filtering.motion.MotionFilter`. 

All buffers contain callable logic to empty thier contents to disk. To when this is triggered, an auxhillary buffer is switched in, to allow for continuous recording around IO access latency.

All buffers are sized to be 10 seconds in video length with the H264 bitrate set to 17000000 bits/second
"""
from dataclasses import dataclass
from collections import deque
from threading import Thread
import numpy as np
import psutil 
from os import nice
from time import time, sleep
from struct import pack
from pathlib import Path
from typing import Tuple


try:
    from picamera import PiCamera
    from picamera.array import PiMotionAnalysis
    from picamera.streams import PiCameraCircularIO, CircularIO
    from picamera.frames import PiVideoFrame, PiVideoFrameType
except (OSError, ModuleNotFoundError):
    # Ignore error that occurs when running pdoc3
    class PiMotionAnalysis:
        pass

from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.imdecode import YUV_BYTE_PER_PIX
from DynAIkonTrap.settings import (
    MotionFilterSettings,
)

from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)

#buffer size (seconds)
BUFF_SZ_S = 10
#bitrate for H264 stream 
BITRATE = 17000000


@dataclass
class MotionData:
    """Class for holding a motion vector data type"""

    motion_dtype = np.dtype(
        [
            ("x", "i1"),
            ("y", "i1"),
            ("sad", "u2"),
        ]
    )


class MotionRAMBuffer(PiMotionAnalysis):
    """This class buffers motion vectors in RAM, runs a motion filter on each set of frame vectors and deposits buffers to disk when an event is required to be saved.

    Buffering is implemented by making use of two :class:`CircularIO` ring buffers - refered to as active and inactive streams. The active stream is being written when the camera is on and producing motion vectors. When saving is requested, the active and inactive streams are swapped, and the new inactive stream is written to disk and it's contents deleted. Motion vectors to be processed are added to an internal process queue, this ensures that the motion detector may skip over processing some vectors if filtering is taking too long per vector frame.

    Motion presence is accessible via a flag variable, is_motion.
    """

    def __init__(
        self,
        camera: PiCamera,
        settings: MotionFilterSettings,
        context_len_s: float,
    ) -> None:
        """Initialiser, creates two instances of :class:`CircularIO`. Each sized to be large enough to hold several seconds (configurable) of motion vector data.

        Args:
            camera (DynCamera): Camera instance buffering from
            settings (MotionFilterSettings): Settings for configuration of the motion filter.
            seconds (float): Number of seconds of motion vectors to buffer.
            context_len_s (float): Context and tail length for the detections.
        """
        (width, height) = camera.resolution
        (self._rows, self._cols) = MotionRAMBuffer.calc_rows_cols(width, height)
        self._element_size: int = MotionRAMBuffer.calc_motion_element_size(
            self._rows, self._cols
        )
        self._active_stream: CircularIO = CircularIO(
            self._element_size * BUFF_SZ_S * camera.framerate
        )
        self._inactive_stream: CircularIO = CircularIO(
            self._element_size * BUFF_SZ_S * camera.framerate
        )
        self._bytes_written: int = 0
        self._framerate = camera.framerate
        self._motion_divisor = 1
        self._motion_filter = MotionFilter(
            settings, camera.framerate / self._motion_divisor
        )
        self._context_len_s: float = context_len_s
        self._proc_queue = deque([], maxlen=100)
        self._target_time: float = 1.0 / camera.framerate
        self.is_motion: bool = False
        self._threshold_sotv: float = settings.sotv_threshold
        self._time_queue = deque([], maxlen=100)
        super().__init__(camera)

        self._proc_thread = Thread(
            target=self._process_queue, name="motion process thread", daemon=True
        )
        self._proc_thread.start()

    def analyse(self, motion):
        """Add motion data to the internal process queue for analysis

        Args:
            motion : motion data to be added to queue
        """
        self._proc_queue.append(motion)

    def _process_queue(self):
        """This function processes vectors on the internal process queue to filter for motion. An aim is to compute motion detection within half a frame interval, as defined by the field _target_time. On some hardware platforms and some resolutions, detection time may go over this budget. In these cases, this function skips computing the next few vector frames to make up for lost time.
        In any case, this function writes a timestamp, motion score and motion vector data to the active stream. If the motion score has not been computed, a value of -1 is written instead.
        """
        p = psutil.Process()
        p.ionice(psutil.IOPRIO_CLASS_BE, 0)
        nice(0)
        skip_frames = 0
        count_frames = 0
        while True:
            try:
                if(len(self._proc_queue)):
                    buf = self._proc_queue.popleft()
                    motion_frame = np.frombuffer(buf, MotionData.motion_dtype)
                    motion_frame = motion_frame.reshape((self.rows, self.cols))
                    motion_score: float = -1.0
                    if (count_frames % self._motion_divisor) == 0:
                        t1 = time()
                        motion_score = self._motion_filter.run_raw(
                            motion_frame)
                        self.is_motion = motion_score > self._threshold_sotv
                        elapsed = time() - t1
                        self._time_queue.append(elapsed)
                    count_frames += 1
                    motion_bytes = (
                        pack("d", float(time()))
                        + pack("d", float(motion_score))
                        + bytearray(motion_frame)
                    )
                    self._bytes_written += self._active_stream.write(
                        motion_bytes)
                else:
                    sleep(0.1)

            except IndexError as e:
                logger.error(
                    "Motion computation Index Error. (IndexError `{}`)".format(
                        e)
                )
                sleep(0.1)
                pass

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        Args:
            filename (Path): path to file
            is_start (bool): indicates if this buffer starts a new motion event
        """
        if is_start:

            current_pos = self._inactive_stream.tell()
            context_pos = max(
                0,
                int(
                    current_pos
                    - (self._element_size * self._context_len_s * self._framerate)
                ),
            )
            try:
                self._inactive_stream.seek(context_pos)
            except ValueError:
                logger.error(
                    "cannot seek to context position for motion vector buffer, buffer abandoned"
                )
                return self.clear_inactive_stream()
        else:
            self._inactive_stream.seek(0)

        with open(filename, "ab") as output:
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self.clear_inactive_stream()

    def clear_inactive_stream(self):
        """Deletes data in the inactive stream, sets stream position to 0."""
        self._inactive_stream.seek(0)
        self._inactive_stream.truncate()

    def switch_stream(self):
        """switch the active and inactive streams"""
        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )

    def calc_rows_cols(width: int, height: int) -> Tuple[int, int]:
        """Calculates the dimensions of motion vectors given a resolution

        Args:
            width (int): resolution width in pixels
            height (int):  resolution height in pixels

        Returns:
            Tuple[int, int]: motion vector row, column dimensions
        """
        cols = ((width + 15) // 16) + 1
        rows = (height + 15) // 16
        return (rows, cols)

    def calc_motion_element_size(rows: int, cols: int) -> int:
        """Calculates the size of a single motion element in the ring buffer

        Args:
            rows (int): motion vector row dimension
            cols (int): motion vector column dimension

        Returns:
            int: size (in bytes) of a single motion element. Computed as size of 2 floats (16 bytes) plus size of all motion vectors to fit input dimensions
        """
        return (len(pack("d", float(0.0))) * 2) + (
            rows * cols * MotionData.motion_dtype.itemsize
        )

    def get_avg_motion_compute_time(self) -> float:
        """Calculates and returns the average motion computation time over the internal _time_queue. 

        Returns:
            float: The average time to compute motion for each frame, returns -1.0 if the queue is empty. 
        """
        if len(self._time_queue) > 0:
            return (sum(self._time_queue) / len(self._time_queue))
        else:
            return -1.0

class VideoRAMBuffer:
    """Class for storing video frames in RAM while motion detection is evaluated.

    Buffering is implemented by making use of two :class:`PiCameraCircularIO` ring buffers - refered to as active and inactive streams. The active stream is being written when the camera is on and producing frames. When saving is requested, the active and inactive streams are swapped, and the new inactive stream is written to disk and it's contents deleted.
    """

    def __init__(self, camera: PiCamera, splitter_port: int, size: int = ((BITRATE // 8) * BUFF_SZ_S)) -> None:
        """Initialise stream object.

        Args:
            camera (DynCamera): Camera instance
            splitter_port (int): Splitter port number, range [1-3], indicates PiCamera port for connection to underlying stream
            size (int): Maximum size of a ring buffer, measured in bytes

        """
        self._active_stream: PiCameraCircularIO = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._inactive_stream: PiCameraCircularIO = PiCameraCircularIO(
            camera, size=size, splitter_port=splitter_port
        )
        self._bytes_written: int = 0
        self._framerate = camera.framerate
        self._frac_full: float = 0.0

    def write(self, buf):
        """Write a frame buffer to the active stream

        Args:
            buf : frame buffer
        """
        self._bytes_written += self._active_stream.write(buf)

    def switch_stream(self):
        """switch the active and inactive streams"""

        self._active_stream, self._inactive_stream = (
            self._inactive_stream,
            self._active_stream,
        )

    def write_inactive_stream(self, filename: Path):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        Args:
            filename (Path): path to file
        """
        with open(filename, "ab") as output:
            while True:
                buf = self._inactive_stream.read1()
                if not buf:
                    break
                output.write(buf)
        self.clear_inactive_stream()

    def clear_inactive_stream(self):
        """Deletes the inactive stream"""
        self._inactive_stream.seek(0)
        self._inactive_stream.clear()


class H264RAMBuffer(VideoRAMBuffer):
    """This class inherits from :class:`~DynAIkonTrap.camera_to_disk.VideoRAMBuffer` to specialise for H264 image encoded frames."""

    def __init__(self, context_length_s, *args, **kwargs) -> None:
        self._context_length_s = context_length_s
        sz = (BITRATE * BUFF_SZ_S) // 8
        super(H264RAMBuffer, self).__init__(size=sz, *args, **kwargs)

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        May be used to start an event stream if is_start is set True. In this case, this function will recall frames from the buffer which occupy the context time. When a stream is started, this function searches for the nearest SPS header to start the H264 encoded stream. As a result, the start index may not be exactly equal to context start time index. The affect of this can be limited by increasing intra-frame frequency - at the expense of stream compression ratio.

        Args:
            filename (Path): path to write the stream to
            is_start (bool, optional): Indicates if this should start a new event stream on disk. Defaults to False.
        """
        if is_start:
            try:
                lst_frames = list(self._inactive_stream.frames)
                # get context index
                context_index = int(
                    round(
                        max(
                            0,
                            len(lst_frames)
                            - (self._context_length_s * self._framerate),
                        )
                    )
                )
                # get sps frame indexes
                sps_frames = list(
                    filter(
                        lambda element: element[1].frame_type
                        == PiVideoFrameType.sps_header,
                        enumerate(lst_frames),
                    )
                )
                if len(sps_frames) > 0:

                    def get_closest_frame(frame_idx, sps_frames):
                        return min(
                            sps_frames,
                            key=lambda element: abs(
                                element[0] - context_index),
                        )[1]

                    # scroll to start frame, sps frame closest to context index
                    start_frame = get_closest_frame(context_index, sps_frames)
                    self._inactive_stream.seek(start_frame.position)
                    return super().write_inactive_stream(filename)
                else:
                    # if no sps frames, discard the stream
                    self.clear_inactive_stream()
            except (IndexError, ValueError) as e:
                logger.error(
                    "Problem writing the first H264 frame, buffer abandoned. (IndexError, ValueError `{}`)".format(
                        e
                    )
                )
                self.clear_inactive_stream()
        else:
            self._inactive_stream.seek(0)
            return super().write_inactive_stream(filename)
    
class RawRAMBuffer(VideoRAMBuffer):
    """This class inherits from :class:`~DynAIkonTrap.camera_to_disk.VideoRAMBuffer` to specialise for raw format image frames."""

    def __init__(self, context_length_s, camera: PiCamera, dim : Tuple[int, int],  *args, **kwargs) -> None:
        self._context_length_s = context_length_s
        sz = int(dim[0] * dim[1] * YUV_BYTE_PER_PIX * BUFF_SZ_S * camera.framerate)
        super(RawRAMBuffer, self).__init__(camera, size=sz, *args, **kwargs)

    def write_inactive_stream(self, filename: Path, is_start=False):
        """Dump the inactive stream to file, then delete it's contents, will append to existing files.

        May be used to start an event stream if is_start is set True. In this case, this function will recall frames from the buffer which occupy the context time.

        Args:
            filename (Path): path to write the stream to
            is_start (bool, optional): Indicates if this should start a new event stream on disk. Defaults to False.
        """
        if is_start:
            lst_frames = list(self._inactive_stream.frames)
            context_index = int(
                round(
                    max(
                        0,
                        len(lst_frames)
                        - (self._context_length_s * self._framerate),
                    )
                )
            )
            start_frame = lst_frames[context_index]
            self._inactive_stream.seek(start_frame.position)
            return super().write_inactive_stream(filename)

        else:
            self._inactive_stream.seek(0)
            return super().write_inactive_stream(filename)
