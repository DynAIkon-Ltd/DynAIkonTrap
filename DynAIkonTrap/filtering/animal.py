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
This module provides a generic interface to an animal detector. The system is fairly agnostic of the specific animal detection mechanism beings used, as the input to the :class:`AnimalFilter` is a JPEG, RGB or RGBA image and the output a confidence in the image containing an animal.

The animal detection model may be chosen from a range of pre-trained detector networks, configurable via :class:`~DynAIkonTrap.settings.AnimalFilterSettings`. Choices currently range between: a SSDLite MobileNet v2 model trained on WCS data, int32 quantised, a SSDLite MobileNet v2 model trained on human and WCS data, int32 quantised and a YOLOv4-tiny model trained on WCS data

The function, :func:`AnimalFilter.run` produces a tuple result, the first result indicates animal presence; the second result human presence. If the model used is trained on WCS data only, the second result will always be False
"""
from dataclasses import dataclass
from enum import Enum
import json
from tempfile import NamedTemporaryFile
from tokenize import endpats
from typing import Tuple, Union, overload
from math import sqrt
import cv2
from cv2 import imwrite
import numpy as np
import time
from requests import HTTPError, RequestException, post, get, request
from pkg_resources import resource_filename

from DynAIkonTrap.settings import AnimalFilterSettings, SenderSettings
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.imdecode import decoder

logger = get_logger(__name__)

RESULTS_ENDPOINT = '/api/v2/predictions/results'
RETRIES = 100
TFL = True
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    logger.error(
        "Cannot import TFLite runtime, execution will fall back to default animal detector, no human filtering"
    )
    TFL = False


@dataclass
class CompressedImageFormat(Enum):
    """Class to store supported compressed image formats"""

    JPEG = 0


@dataclass
class NetworkInputSizes:
    """A class to hold data for neural network input buffer sizes. Sizes are in (width, height) format"""

    YOLOv4_TINY = (416, 416)
    SSDLITE_MOBILENET_V2 = (300, 300)


class AnimalFilter:
    """Animal filter stage to indicate if a frame contains an animal"""

    def __init__(self, settings: AnimalFilterSettings, sender_settings: SenderSettings =None):
        """
        Args:
            settings (AnimalFilterSettings): Settings for the filter
        """
        self.animal_threshold = settings.animal_threshold
        self.human_threshold = settings.human_threshold
        self.detect_humans = settings.detect_humans
        self.fast_animal_detect = settings.fast_animal_detect
        self.use_fcc = settings.fastcat_cloud_detect
        self.yuv_dims = (0,0)

        if settings.detect_humans or settings.fast_animal_detect:
            self.input_size = NetworkInputSizes.SSDLITE_MOBILENET_V2
            if settings.detect_humans:
                self.model = tflite.Interpreter(
                    model_path=resource_filename("DynAIkonTrap", "filtering/models/ssdlite_mobilenet_v2_animal_human/model.tflite")

                )
            elif settings.fast_animal_detect:
                self.model = tflite.Interpreter(
                    model_path=resource_filename("DynAIkonTrap", "filtering/models/ssdlite_mobilenet_v2_animal_only/model.tflite")
                )
            self.model.resize_tensor_input(
                0, [1, self.input_size[0], self.input_size[1], 3], strict=True
            )
            self.model.allocate_tensors()
            self.tfl_input_details = self.model.get_input_details()
            self.tfl_output_details = self.model.get_output_details()

        else:
            # use YOLOv4-tiny 416 animal-only detector
            self.input_size = NetworkInputSizes.YOLOv4_TINY
            self.model = cv2.dnn.readNet(
                resource_filename("DynAIkonTrap", "filtering/yolo_animal_detector.weights"),
                resource_filename("DynAIkonTrap", "filtering/yolo_animal_detector.cfg"),
            )
            layer_names = self.model.getLayerNames()
            self.output_layers = [
                layer_names[i[0] - 1] for i in self.model.getUnconnectedOutLayers()
            ]
        if sender_settings is not None and settings.fastcat_cloud_detect:
            self.url_post = sender_settings.server + sender_settings.POST + "?modelId=" + sender_settings.modelId
            self.url_get = sender_settings.server + RESULTS_ENDPOINT

    def run_raw_fcc(
        self,
        image: bytes,
        is_jpeg: bool=False
    ) -> float:
        """A function to run the animal detection method by querying the FASTCAT-Cloud Web API 

        Args:
            image (bytes):  The image frame to be analysed, can be in JPEG compressed format or YUV420 raw format
            is_jpeg (bool, optional):  used to inform buffer reading, set to `True` if a jpeg is given, `False` for YUV420 buffer. Defaults to `False`.

        Returns:
            float: The score of the highest confidence animal bounding box, as returned by FASTCAT-Cloud API
        """
        files = []
        if is_jpeg:
            temp_file = NamedTemporaryFile(suffix='.png', delete=False)
            image_file = temp_file.name
            try:
                cv2.imwrite(image_file, image)
            except cv2.error:
                logger.error('Error saving frame for FASTCAT-Cloud upload: {}'.format(e))
                return 0.0
        else: 
            image_file = decoder.yuv_to_png_temp_file(image, self.yuv_dims)
        requestId=""
        try:
            with open(image_file, 'rb') as f:
                r = post(self.url_post, files=[('image', (image_file, f, 'image/png'))], timeout=3)
                r.raise_for_status()  
                result = r.json()
                if result['message'] == 'Success.':
                    requestId=result['body']['predictionRequestPublicId']
                else:
                    logger.error("Error getting detection from FASTCAT-Cloud: {}".format(result))
                    return 0.0
        except HTTPError as e:
            logger.error("HTTP error during FASTCAT-Cloud animal detection, POST: {}".format(e))
            return 0.0
        except ConnectionError as e:
            logger.error("Connection error during FASTCAT-Cloud animal detection, POST {}".format(e))
            return 0.0
        except RequestException as e:
            logger.error("Requests error during FASTCAT-Cloud animal detection, POST: {}".format(e))
            return 0.0
        try:
            r = get(self.url_get + '?predictionRequestPublicId='+requestId)
            r.raise_for_status()
            result=r.json()
            tries=1
            while result['message'] == 'No results found for this query.' and tries < RETRIES:
                #wait for result to become available...
                time.sleep(5)
                r = get(self.url_get + '?predictionRequestPublicId='+requestId)
                r.raise_for_status()
                result=r.json()
                tries += 1
                
            if result['message'] == 'Success.':
                detections=json.loads(result['body']['formattedResults'][0]['classifications'][0]["Results"])
                if detections != "[]" and len(detections) > 0:                
                    detections=sorted(detections, key=lambda x: x['score'], reverse=True)
                    return detections[0]['score']
                else:
                    return 0.0
            else:
                logger.error("Error getting detection from FASTCAT-Cloud: {}".format(result))
                return 0.0
        except HTTPError as e:
            logger.error("HTTP error during FASTCAT-Cloud animal detection, GET: {}".format(e))
            return 0.0
        except ConnectionError as e:
            logger.error("Connection error during FASTCAT-Cloud animal detection, GET: {}".format(e))
            return 0.0
        except RequestException as e:
            logger.error("Requests error during FASTCAT-Cloud animal detection, GET: {}".format(e))
            return 0.0
        return 0.0


            
    def run_raw(
        self,
        image: bytes,
        is_jpeg : bool = False,
    ) -> Tuple[float, float]:
        """Run the animal filter on the image to give a confidence that the image frame contains an animal and/or a human. For configurations where an animal-only detector is initialised, human confidence will always equal 0.0.

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or YUV420 raw format
            is_jpeg (bool, optional): used to inform buffer reading, set to `True` if a jpeg is given, `False` for YUV420 buffer. Defaults to `False`.

        Returns:
            Tuple(float, float): Confidences in the output containing an animal and a human as a decimal fraction in range (0-1)
        """
        if self.use_fcc:
            fcc_result = self.run_raw_fcc(image, is_jpeg)
            return fcc_result, 0.0
        else:
            decoded_image = []
            if is_jpeg:
                decoded_image = decoder.jpg_buf_to_bgr_array(image)
            else: 
                decoded_image = decoder.yuv_buf_to_bgr_array(image, self.yuv_dims)
            decoded_image = cv2.resize(decoded_image, (self.input_size))
            animal_confidence = 0.0
            human_confidence = 0.0
            if self.detect_humans or self.fast_animal_detect:

                # convert to floating point input
                # in future, tflite conversion process should be modified to accept int input, it's not clear how that's done yet
                decoded_image = decoded_image.astype("float32")
                decoded_image = decoded_image / 255.0
                model_input = [decoded_image]
                self.model.set_tensor(self.tfl_input_details[0]["index"], model_input)
                self.model.invoke()
                output_confidences = self.model.get_tensor(
                    self.tfl_output_details[0]["index"]
                )[0]
                if self.detect_humans:
                    output_classes = self.model.get_tensor(
                        self.tfl_output_details[3]["index"]
                    )[0].astype(int)
                    human_indexes = [
                        i for (i, label) in enumerate(output_classes) if label == 0
                    ]
                    animal_indexes = [
                        i for (i, label) in enumerate(output_classes) if label == 1
                    ]
                    if human_indexes:
                        human_confidence = max(
                            [output_confidences[i] for i in human_indexes]
                        )
                    if animal_indexes:
                        animal_confidence = max(
                            [output_confidences[i] for i in animal_indexes]
                        )
                else:
                    animal_confidence = max(output_confidences)

            else:
                blob = cv2.dnn.blobFromImage(
                    decoded_image, 1, NetworkInputSizes.YOLOv4_TINY, (0, 0, 0)
                )

                blob = blob / 255.0  # Scale to be a float
                self.model.setInput(blob)
                output = self.model.forward(self.output_layers)
                _, _, _, _, _, confidence0 = output[0].max(axis=0)
                _, _, _, _, _, confidence1 = output[1].max(axis=0)
                animal_confidence = max(confidence0, confidence1)
            return animal_confidence, human_confidence

    def run(
        self,
        image: bytes,
        is_jpeg : bool = False
    ) -> Tuple[bool, bool]:
        """The same as :func:`run_raw()`, but with a threshold applied. This function outputs a boolean to indicate if the confidences are at least as large as the threshold

        Args:
            image (bytes): The image frame to be analysed, can be in JPEG compressed format or YUV420 raw format
            is_jpeg (bool, optional): used to inform buffer reading, set to `True` if a jpeg is given, `False` for YUV420 buffer. Defaults to `False`.

        Returns:
            Tuple(bool, bool): Each element is `True` if the confidence is at least the threshold, otherwise `False`. Elements represent detections for animal and human class.        
        """
        start_time = time.time()
        animal_confidence, human_confidence = self.run_raw(image, is_jpeg)
        animal_confidence_rounded = round(animal_confidence,  2)
        human_confidence_rounded = round(human_confidence, 2)
        animal_confidence_display = "<" if animal_confidence < animal_confidence_rounded  else ">="
        animal_confidence_display += str(animal_confidence_rounded)
        human_confidence_display = "<" if human_confidence < human_confidence_rounded else ">="
        human_confidence_display += str(human_confidence_rounded)
        logger.info(
            "Deep network inference run. Propagation latency: {:.2f}secs. Animal Confidence :{}%. Human Confidence :{}%.".format(
                time.time() - start_time, animal_confidence_display, human_confidence_display
            )
        )
        return (
            animal_confidence >= self.animal_threshold,
            human_confidence >= self.human_threshold,
        )
