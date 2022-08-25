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
Provides a simple interface for processing captured events from :class: `~DynAIkonTrap.filtering.remember_from_disk.EventRememberer`. Encapsulated are methods for iterating over an event in spiral inference pattern, and running inference by calling `~DynAIkonTrap.filtering.animal.AnimalFilter`.

Events are loaded from disk before frames are processed to keep memory usage at sensible levels, each frame is loaded only when required for inference with multiple read operations requested throughout processing an event. Indices of each frame data are assumed to already have been tagged within the :class: `~DynAIkonTrap.filtering.remember_from_disk.EventData` class.

The main method, () returns

"""
from typing import Tuple
from numpy import round, linspace
from os.path import basename, join
from subprocess import CalledProcessError, check_call


from DynAIkonTrap.filtering.animal import AnimalFilter
from DynAIkonTrap.filtering.remember_from_disk import EventData
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


class EventProcessor:

    def __init__(self, animal_detector: AnimalFilter, event_fraction: float):
        self._event_fraction = event_fraction
        self._animal_filter = animal_detector
        pass

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
        #from the event, get the list of file offsets for each frame
        frame_file_offsets = list(event.raw_raster_file_indices)
        logger.info("Processing event with {} raw image frames.".format(
            len(frame_file_offsets)))
        inf_count = 0
        if len(frame_file_offsets) > 0:
            #get index of the middle frame in file offsets array
            middle_idx_file_offsets = len(frame_file_offsets) // 2
            if self._event_fraction <= 0:
                # run detector on middle frame only
                frame = self._get_frame_from_index(
                    event, middle_idx_file_offsets)
                is_animal, is_human = self._animal_filter.run(
                    frame
                )
                inf_count += 1
                return (is_animal and not is_human, inf_count)
            else:
                # get evenly spaced indices for frame offsets throughout the event
                nr_elements = int(round(len(frame_file_offsets) * self._event_fraction))
                indices = [
                    int(round(index)) for index in linspace(0, len(frame_file_offsets) - 1, nr_elements)
                ]
                # order in "spiral out" from the center frame 
                indices.sort(key=lambda x: abs(middle_idx_file_offsets - x))
                # process frames, starting from the middle
                for index in indices:
                    frame = self._get_frame_from_index(
                        event, index)
                    is_animal, is_human = self._animal_filter.run(
                        frame
                    )
                    inf_count += 1
                    if is_human:
                        return False, inf_count
                    if is_animal:
                        return True, inf_count
        return False, inf_count

    def _get_frame_from_index(self, event: EventData, frame_offset_indx: int) -> bytes:
        """Extracts the frame from disk for a given event and frame index in file, returns that frame as a byte buffer

        Args:
            event (EventData): given event to extract the frame from 
            frame_offset_indx (int): the index required to find the frames file offset in the event.raw_raster_file_indices

        Returns:
            bytes: a buffer of bytes of the frame at the given index 
        """
        buf = 0
        raw_raster_path = join(event.dir, 'clip.dat')
        read_size_b = -1
        if frame_offset_indx + 1 < len(event.raw_raster_file_indices):
            read_size_b =  event.raw_raster_file_indices[frame_offset_indx + 1] - event.raw_raster_file_indices[frame_offset_indx]
        with open(raw_raster_path, "rb") as file:
            file.seek(event.raw_raster_file_indices[frame_offset_indx])
            buf = file.read(read_size_b)            
        return buf

    @staticmethod
    def delete_event(event: EventData):
        """Static method to delete an event on disk. 

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
                logger.info("Deleted event with directory {}".format(event.dir))
        except CalledProcessError as e:
            logger.error(
                "Problem deleting event with directory: {}. (CalledProcessError) : {}".format(
                    event.dir, e
                )
            )
