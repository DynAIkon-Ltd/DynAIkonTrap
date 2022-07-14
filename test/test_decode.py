from unittest import TestCase
from os.path import isfile
import cv2

from DynAIkonTrap.imdecode import decoder

class TestH264toJpg(TestCase):

    def setUp(self):
        self._h264_filename = 'test/data/event_example/clip.h264'

    def test_H264_decoding(self):
        ret = decoder.h264_to_jpeg_frames(self._h264_filename)
        #nr of frames for this file is known at 385
        self.assertTrue(len(ret) == 385)
        #check each of the files can be opened and read
        for file in ret:
            with open(file) as f:
                self.assertTrue(f.readable())

    def test_H264_bogus_file(self):
        ret = decoder.h264_to_jpeg_frames('this_is_not_a_real_file.h264')
        self.assertTrue(len(ret) == 0)

class TestH264toMp4Avi(TestCase):

    def setUp(self) -> None:
        self._h264_filename = 'test/data/event_example/clip.h264'
    
    def test_H264_to_mp4(self):
        ret = decoder.h264_to_mp4(self._h264_filename, 20) 
        #check file exists
        self.assertTrue(isfile(ret))
        #check stream can be read with cv2
        vidcap = cv2.VideoCapture(ret)
        success, im1 = vidcap.read()
        self.assertTrue(success)
        self.assertIsNotNone(im1)
        
    
