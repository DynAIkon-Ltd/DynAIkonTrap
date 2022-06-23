import cv2
import numpy as np
from PIL import Image
from math import sqrt

class decoder:
    @staticmethod
    def yuv_buf_to_rgb_array(buf : bytes) -> np.ndarray:
        """_summary_

        Args:
            buf (bytes): _description_
            fheight (int): _description_
            fwidth (int): _description_

        Returns:
            np.ndarray: _description_
        """
        sz = int(sqrt(len(buf) / 1.5))
        fheight = fwidth = sz
        Y_end = int(fheight * fwidth)
        U_end = Y_end + int((fheight//2) * (fwidth//2))
        #get Y values, first 2/3rds
        Y = np.frombuffer(buf[0:Y_end], dtype=np.uint8).reshape((fheight, fwidth))
        #get U values, next 1/6th
        U = np.frombuffer(buf[Y_end:U_end], dtype=np.uint8).reshape((fheight//2, fwidth//2)).repeat(2, axis=0).repeat(2, axis=1)
        #get V values, final 1/6th
        V = np.frombuffer(buf[U_end:], dtype=np.uint8).reshape((fheight//2, fwidth//2)).repeat(2, axis=0).repeat(2, axis=1)
        #stack to form YUV array
        YUV = np.dstack((Y, U, V))[:fwidth, :fheight, :].astype(np.float)
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
    def jpg_buf_to_rgb_array(buf : bytes) -> np.ndarray:
        """_summary_

        Args:
            buf (bytes): _description_

        Returns:
            np.ndarray: _description_
        """
        return cv2.imdecode(np.asarray(buf), cv2.IMREAD_COLOR)

    
    @staticmethod
    def im_resize(im: np.ndarray, w : int, h : int) -> np.ndarray:
        return cv2.resize(im, (w, h))


