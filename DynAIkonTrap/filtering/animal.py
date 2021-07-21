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
This module provides a generic interface to an animal detector. The system is fairly agnostic of the specific animal detection mechanism beings used, as the input to the `AnimalFilter` is a JPEG image and the output a confidence in the image containing an animal.

A WCS-trained Tiny YOLOv4 model is used in this implementation, but any other architecture could be substituted in its place easily. Such a substitution would not require any changes to the module interface.
"""
import cv2
import numpy as np
import tflite_runtime.interpreter as tflite  

from DynAIkonTrap.settings import AnimalFilterSettings


class AnimalFilter:
    """Animal filter stage to indicate if a frame contains an animal
    """
    def __init__(self, settings: AnimalFilterSettings):
        """
        Args:
            settings (AnimalFilterSettings): Settings for the filter
        """
        self.threshold = settings.threshold

        self.tfl_runner = tflite.Interpreter(
                model_path="DynAIkonTrap/filtering/model.tflite"
                )
        self.tfl_runner.allocate_tensors()
        self.input_details = self.tfl_runner.get_input_details()
        self.output_details = self.tfl_runner.get_output_details()

    def run_raw(self, image: bytes) -> float:
        """Run the animal filter on the image to give a confidence that the image frame contains an animal

        Args:
            image (bytes): The image frame to be analysed in JPEG format

        Returns:
            float: Confidence in the output containing an animal as a decimal fraction
        """
        decoded_image = cv2.resize(
            cv2.imdecode(np.asarray(image), cv2.IMREAD_COLOR), (300, 300)
        )
        resized_image = decoded_image / 255.
        resized_image = resized_image.astype(np.float32)
        tfl_img = np.array([resized_image])
        self.tfl_runner.set_tensor(self.input_details[0]["index"], tfl_img)
        self.tfl_runner.invoke()
        tfl_out_classes = self.tfl_runner.get_tensor(self.output_details[1]["index"])[0].tolist()
        #obtain indexes of animal only classes (ie in range 15-24)
        indexes = [idx for idx, detection in enumerate(tfl_out_classes) if (14.0 < detection < 25.0 | detection == 1.0)]  
        tfl_out_scores = self.tfl_runner.get_tensor(self.output_details[2]["index"])[0].tolist()
        #get detection with highest confidence - this is a hack, not required for a network trained on animals only
        max_confidence = 0.0
        for idx in indexes:
            if tfl_out_scores[idx] > max_confidence:
                max_confidence = tfl_out_scores[idx]
    
        return max_confidence

    def run(self, image: bytes) -> bool:
        """The same as `run_raw()`, but with a threshold applied. This function outputs a boolean to indicate if the confidence is at least as large as the threshold

        Args:
            image (bytes): The image frame to be analysed in JPEG format

        Returns:
            bool: `True` if the confidence in animal presence is at least the threshold, otherwise `False`
        """
        return self.run_raw(image) >= self.threshold
