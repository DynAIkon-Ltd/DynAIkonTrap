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
A simple interface to the frame animal filtering pipelines is provided by this module. It encapsulates both motion- and image-based filtering as well as any smoothing of this in time. Viewed from the outside the :class:`Filter` may read from :class:`~DynAIkonTrap.camera.Camera`'s output and in turn outputs only frames containing animals. Alternatively, :class:`Filter` may read from :class:`~DynAIkonTrap.filtering.remember_from_disk.EventRememberer` to process motion events stored on disk. As a result, the filter may operate in two modes: a) filter BY_FRAME, b) filter BY_EVENT.

In the filter BY_FRAME mode, frames are first analysed by the :class:`~DynAIkonTrap.filtering.motion.MotionFilter`. Frames with motion score and label indicating motion, are added to a :class:`~DynAIkonTrap.filtering.motion_queue.MotionLabelledQueue`. Within the queue the :class:`~DynAIkonTrap.filtering.animal.AnimalFilter` stage is applied with only the animal frames being returned as the output of this pipeline.

In the filter BY_EVENT mode, events are loaded from the instance of :class:`~DynAIkonTrap.filtering.remember_from_disk.EventRememberer` and processed within :func:`_process_event()`. This method employs a spiral-out inference strategy which checks each frame for animal detection (starting in the center frame, working outwards) animal detection is performed by applying :class:`~DynAIkonTrap.filtering.animal.AnimalFilter`. 

In both modes, the output is accessible via a queue. BY_FRAME mode produces a queue of frames containing animals, BY_EVENT mode produces a queue of events containing animal frames. This allows the pipeline to be run in a separate process.
"""
from asyncio.windows_events import NULL
from multiprocessing import Process, Queue
from multiprocessing.context import set_spawning_popen
from multiprocessing.queues import Queue as QueueType
from queue import Empty
from os import nice
from os.path import basename
from shutil import rmtree
from subprocess import CalledProcessError, call, check_call
from time import sleep
from time import time
from enum import Enum
from typing import Union, Tuple
from numpy import round, linspace

from DynAIkonTrap.camera import Frame, Camera
from DynAIkonTrap.filtering import motion_queue
from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.motion import MotionFilter
from DynAIkonTrap.filtering.motion_queue import MotionLabelledQueue
from DynAIkonTrap.filtering.motion_queue import MotionStatus
from DynAIkonTrap.filtering.remember_from_disk import EventData, EventRememberer
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import FilterSettings, RawImageFormat

logger = get_logger(__name__)


class FilterMode(Enum):
    """A class to configure the mode the filter operates in"""
    BY_FRAME = 0
    BY_EVENT = 1


class Filter:
    """Wrapper for the complete image filtering pipeline"""

    def __init__(
        self, read_from: Union[Camera, EventRememberer], settings: FilterSettings
    ):
        """
        Args:
            read_from (Union[Camera, EventRememberer]): Read frames from camera or EventRememberer
            settings (FilterSettings): Settings for the filter pipeline
        """

        self._input_queue = read_from
        self.framerate = read_from.framerate
        self.raw_bpp = read_from.raw_bpp
        self.raw_dims = read_from.raw_dims

        self._animal_filter = AnimalFilter(settings=settings.animal)

        if isinstance(read_from, Camera):
            self.mode = FilterMode.BY_FRAME
            self._output_queue: QueueType[Frame] = Queue()
            self._motion_filter = MotionFilter(
                settings=settings.motion, framerate=self.framerate
            )
            self._motion_threshold = settings.motion.sotv_threshold
            self._motion_labelled_queue = MotionLabelledQueue(
                animal_detector=self._animal_filter,
                settings=settings.processing,
                framerate=self.framerate,
            )

            self._usher = Process(target=self._handle_input_frames, daemon=True)
            logger.debug("Filter started, filtering with mode: BY_FRAME")
            self._usher.start()

        elif isinstance(read_from, EventRememberer):
            self.mode = FilterMode.BY_EVENT
            self._event_fraction = settings.processing.detector_fraction
            self._raw_image_format = read_from.raw_image_format
            self._output_queue: QueueType[EventData] = Queue(maxsize=1)
            self._usher = Process(target=self._handle_input_events, daemon=True)
            logger.debug("Filter started, filtering with mode: BY_EVENT")
            self._usher.start()

    def get(self) -> Union[EventData, Frame]:
        """Retrieve the next animal `Frame` or animal `EventData` from the filter pipeline's output.

        Returns:
            Next (Union[EventData, Frame]): An animal frame or event
        """
        if self.mode == FilterMode.BY_FRAME:
            return self._motion_labelled_queue.get()
        elif self.mode == FilterMode.BY_EVENT:
            return self._output_queue.get()

    def close(self):
        self._usher.terminate()
        self._usher.join()

    def _handle_input_frames(self):
        """Process input queue as a list of frames: BY_FRAME filter mode."""
        while True:

            try:
                frame = self._input_queue.get()
            except Empty:
                # An unexpected event; finish processing motion so far
                self._motion_labelled_queue.end_motion_sequence()
                self._motion_filter.reset()
                continue

            motion_score = self._motion_filter.run_raw(frame.motion)
            motion_detected = motion_score >= self._motion_threshold

            if motion_detected:
                self._motion_labelled_queue.put(
                    frame, motion_score, MotionStatus.MOTION
                )

            else:
                self._motion_labelled_queue.put(frame, -1.0, MotionStatus.STILL)

    def _handle_input_events(self):
        """Process input queue as a list of events: BY_EVENT filter mode."""
        nice(5)
        while True:
            try:
                event = self._input_queue.get()
                start_s = time()
                result, nr_inf = self._process_event(event)
                end_s = time() - start_s
                time_taken = (end_s/nr_inf) if nr_inf > 0 else 0
                logger.debug("Event processed in {:.2f}secs, running {} inference(s). Avg execution time per inference: {:.2f}secs".format(
                    end_s,
                    nr_inf,
                    time_taken
                ))
                if not result:
                    logger.info("No Animal detected, deleting event from disk...")
                    self._delete_event(event)
                else:
                    logger.info("Animal detected, save output video...")
                    self._output_queue.put(event)

            except Empty:
                logger.error("Input events queue empty")
                continue

    def _process_event(self, event: EventData) -> Tuple[bool, int]:
        """Processes a given :class:`~DynAIkonTrap.filtering.remember_from_disk.EventData` to determine if it contains an animal. This is achieved by running the saved raw image stream through the animal detector. Detection is performed in a spiral-out pattern, starting at the image in the middle of the event and moving out towards the edges while an animal has not been detected. When an animal detection occurs, this function returns True, this function returns False when the spiral is completed and no animals have been detected.

        Additionally, if the human detection is enabled, this function will also search for a human in the event. This works exactly the same as the animal detection with the exception of detected human presence causing this function to return False.

        A parameter to choose a spiral step size may be declared within :class:`~DynAIkonTrap.settings.ProcessingSettings`, detector_fraction. When set to 1.0, every event image is evaluated in the worst case. Fractional values indicate a number of frames to process per event. The special case, 0.0 evaluates the centre frame only.
        Args:
            event (EventData): Instance of :class:`~DynAIkonTrap.filtering.remember_from_disk.EventData` to filter for animal.

        Returns:
            bool: True if event contains an animal, False otherwise.
            int: number of inferences run on this event to reach conclusion.
        """
        
        frame_indices = list(event.raw_raster_file_indices)
        # frames = list(event.raw_raster_frames)
        logger.debug("Processing event with {} raw image frames.".format(len(frame_indices)))
        middle_idx = len(frame_indices) // 2
        inference_data = []
        human = False
        animal = False
        inf_count = 0
        if self._event_fraction <= 0:
            # run detector on middle frame only
            frame_idx = frame_indices[middle_idx]
            frame = self._get_frame_from_index(event.raw_raster_path, frame_idx)
            is_animal, is_human = self._animal_filter.run(
                frame, img_format=self._raw_image_format
            )
            inf_count += 1
            return (is_animal and not is_human, inf_count)
        else:
            # get evenly spaced frames throughout the event
            nr_elements = int(round(len(frame_indices) * self._event_fraction))
            indices = [
                int(round(index)) for index in linspace(0, len(frame_indices) - 1, nr_elements)
            ]
            lst_indx_frames_from_centre = [(index, frame_indices[index]) for index in indices]
            # sort in ordering from middle frame
            lst_indx_frames_from_centre.sort(key=lambda x: abs(middle_idx - x[0]))
            # process frames from middle, spiral out
            for (index, frame_index) in lst_indx_frames_from_centre:
                frame = self._get_frame_from_index(event.raw_raster_path, frame_index)
                is_animal, is_human = self._animal_filter.run(
                    frame, img_format=self._raw_image_format
                )
                inf_count += 1
                if is_human:
                    return False, inf_count
                if is_animal:
                    return True, inf_count
        return False, inf_count
        
    def _get_frame_from_index(self, raw_path : str, frame_idx : int) -> bytes:
        buf = NULL
        with open(raw_path, "rb") as file:
            file.seek(frame_idx)
            buf = file.read1(
                        self.raw_dims[0] * self.raw_dims[1] * self.raw_bpp
                    )
        return buf    
        
   
    def _delete_event(self, event: EventData):
        """Deletes an event on disk.

        Args:
            event (EventData): Event to be deleted.
        """

        try:
            # check directory is actually an event directory
            name = basename(event.dir)
            if name.startswith("event_"):
                check_call(
                    ["rm -r {}".format(event.dir)],
                    shell=True,
                )
        except CalledProcessError as e:
            logger.error(
                "Problem deleting event with directory: {}. (CalledProcessError) Code: {}".format(
                    event.dir, e.returncode
                )
            )
