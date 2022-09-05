# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2022 Ross Gardiner

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
"""Static functions providing access to decoding byte arrays into image formats, returned data are numpy ndarrays."""
from distutils.log import error
from genericpath import exists
from subprocess import CalledProcessError, check_call
from tempfile import NamedTemporaryFile
from typing import List, Tuple
import cv2
import numpy as np
from math import sqrt
from os.path import join

from DynAIkonTrap.logging import get_logger

YUV_BYTE_PER_PIX = 1.5 

logger = get_logger(__name__)

class decoder:

    """A class containing static methods to decode image formats YUV and JPEG, depends on numpy and opencv (cv2) python packages. YUV formats are assumed to be YUV420, with 1.5 bytes per pixel, as described here: https://en.wikipedia.org/wiki/YUV#Y.E2.80.B2UV420p_.28and_Y.E2.80.B2V12_or_YV12.29_to_RGB888_conversion

    Included methods convert a given byte array into numpy ndarrays of pixel values. 
    """
    @staticmethod
    def yuv_buf_to_bgr_array(buf : bytes, dims: Tuple[int, int]) -> np.ndarray:
        """converts a given byte buffer in YUV420 format into an ndarray of pixel values in BGR format. Code inspired from Picamera example, availble: https://picamera.readthedocs.io/en/release-1.13/recipes2.html#unencoded-image-capture-yuv-format

        Args:
            buf (bytes): a bytes object containing the raw pixel data in YUV format. Dimensions of the buffer are assumed to be square, the width and height are calculated from this from using the buffer length.

        Returns:
            np.ndarray: an ndarray with size (width, height, 3) where each element is a pixel, pixel format is BGR, one byte per colour
        """
        fwidth, fheight = dims
        Y_start = 0
        Y_end = Y_start + int(fheight * fwidth) 
        U_end = Y_end + int((fheight//2) * (fwidth//2))
        #get Y values, first 2/3rds
        Y = np.frombuffer(buf[Y_start:Y_end], dtype=np.uint8).reshape((fheight, fwidth))
        #get U values, next 1/6th
        U = np.frombuffer(buf[Y_end:U_end], dtype=np.uint8).reshape((fheight//2, fwidth//2)).repeat(2, axis=0).repeat(2, axis=1)
        #get V values, final 1/6th
        V = np.frombuffer(buf[U_end:], dtype=np.uint8).reshape((fheight//2, fwidth//2)).repeat(2, axis=0).repeat(2, axis=1)
        #stack to form YUV array
        YUV = np.dstack((Y, U, V))[:fheight, :fwidth, :].astype(np.float)
        YUV[:, :, 0]  = YUV[:, :, 0]  - 16   # Offset Y by 16
        YUV[:, :, 1:] = YUV[:, :, 1:] - 128  # Offset UV by 128
        # YUV conversion matrix from ITU-R BT.601 version (SDTV)
        #              Y       U       V
        M = np.array([[1.164,  0.000,  1.596],    # R
                    [1.164, -0.392, -0.813],    # G
                    [1.164,  2.017,  0.000]])   # B
        # Take the dot product with the matrix to produce RGB output, clamp the
        # results to byte range and convert to bytes
        RGB = YUV.dot(M.T).clip(0, 255).astype(np.uint8)
        BGR = cv2.cvtColor(RGB, cv2.COLOR_RGB2BGR)
        return BGR

    @staticmethod 
    def yuv_to_png_temp_file(buf : bytes) -> str:
        """converts a given buffer in YUV420 format into a temporary png file stored on disk 

        Args:
            buf (bytes):  a bytes object containing the raw pixel data in YUV format. Dimensions of the buffer are assumed to be square, the width and height are calculated from this from using the buffer length.

        Returns:
            str: path to png file on disk, returns empty string if no file could be created
        """
        img_array_bgr = decoder.yuv_buf_to_bgr_array(buf)
        image_file = NamedTemporaryFile(suffix='.png', delete=False)
        ret = ""
        try:
            cv2.imwrite(image_file.name, img_array_bgr)
            ret = image_file.name
        except cv2.error as e: 
            logger.error("YUV -> png conversion error: {}".format(e))
        return ret

    @staticmethod
    def bgr_array_to_yuv_buf(bgr: np.ndarray) -> bytes:
        """Used to convert bgr colour matrices into YUV420 format buffers compatible with the remainder of the LOW_POWERED pipeline

        Args:
            bgr (np.ndarray): Input BGR matrix

        Returns:
            bytes: Output YUV420 format buffer
        """
        
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2YUV_I420).tobytes()

    @staticmethod
    def jpg_buf_to_bgr_array(buf : bytes) -> np.ndarray:
        """Wraps around the OpenCV imdecode method, to decode colour jpeg images produces a numpy ndarray in BGR format of uncompressed data

        Args:
            buf (bytes): a bytes buffer containing image data compressed in jpeg format, data is assumed to be a 3-channel, colour image

        Returns:
            np.ndarray: an ndarray with size (width, height, 3) where each element is a pixel, pixel format is BGR, one byte per colour
        """
        return cv2.imdecode(np.asarray(buf), cv2.IMREAD_COLOR)

    @staticmethod
    def h264_to_jpeg_frames(h264_file : str) -> List[str]:
        """Create a list of jpeg files stored on disk for every frame in the h264 recording file. If no valid file is given, returns empty list

        Args:
            h264_file (str): file path to a h264 encoded recording

        Returns:
            List[str]: list of file paths to saved jpeg images, one per h264 encoded frame. All files saved within the /tmp/ directory for further moving around. If the h264 path given, an empty list is returned
        """
        images = []
        if exists(h264_file):
            try:
                vidcap = cv2.VideoCapture(h264_file)
                success, image = vidcap.read()
                images = []
                while success:
                    image_file = NamedTemporaryFile(suffix='.jpg', delete=False)
                    cv2.imwrite(image_file.name, image)
                    images.append(image_file.name)
                    success, image = vidcap.read()
            except cv2.error as e:
                logger.error("H264 -> images decoding error: {}".format(e))    
        return images

    @staticmethod
    def h264_to_mp4(h264_file: str , video_framerate: int, suffix:str = ".mp4" ) -> str:
        """This wraps H264 files in the mp4 container format, this is performed calling FFMPEG. Video framerate is also required. 
        
        MP4 files may also be passed in place of the h264 input. 

        Args:
            h264_file (str): The path to the h264 (or mp4) file to be converted 
            video_framerate (int): The video framerate 
            suffix (str, optional): An optional video suffix to produce other file formats such as .avi. Defaults to ".mp4".

        Returns:
            str: Path to the generated mp4 file on disk. This file may be empty if the encoding process fails. 
        """
        
        file = NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            check_call(
                [
                    "nice -n 5 ffmpeg -hide_banner -loglevel error -r {} -probesize 42M -i {} -c copy {} -y".format(
                     video_framerate, h264_file, file.name
                    )
                ],
                shell=True,
            )
        except CalledProcessError as e:
            logger.error(
                "Ffmpeg error converting .h264 to {}. Error: {}".format(
                    suffix, e
                )
            )
        return file.name


    

