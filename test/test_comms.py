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
from queue import Queue
from unittest import TestCase
from glob import glob
from os import listdir
from os.path import exists, isfile
import responses
from responses import matchers
from responses.matchers import multipart_matcher

from DynAIkonTrap.comms import Writer, Sender, SensorLogs, Output
from DynAIkonTrap.filtering.remember_from_disk import EventData
from DynAIkonTrap.filtering.filtering import FilterMode
from DynAIkonTrap.settings import OutputSettings, OutputFormat, SenderSettings, SensorSettings, FilterSettings
from DynAIkonTrap.imdecode import decoder

class MockFilter:
    def __init__(self, desired_mode: FilterMode):
        self.queue = Queue()
        self.framerate = 20
        self.mode = desired_mode
       

    def add_to_event_queue(self):
        example_event = EventData(
            dir="test/data/event_example"
        )
        self.queue.put(example_event)

    def get(self):
        return self.queue.get()

class TestsWriterEventModeImagesOut(TestCase):
    def setUp(self) -> None:
        self._writer = Writer(OutputSettings(output_format=OutputFormat.STILL), (MockFilter(
            desired_mode=FilterMode.BY_EVENT), SensorLogs(SensorSettings())))
        return super().setUp()

    def test_output_group_of_stills(self):
        images = decoder.h264_to_jpeg_frames('test/data/event_example/clip.h264')
        directory_name = self._writer.output_group_of_stills(images, 0.0, None)
        #verify directory exists
        self.assertTrue(exists(directory_name))
        #verify directory contains 3 jpeg images
        names = glob(directory_name + '/*.jpg')
        nr_jpegs = len([name for name in names if isfile(name)])
        self.assertTrue(nr_jpegs == 3)

class TestsWriterEventModeVideoOut(TestCase):
    def setUp(self) -> None:
        self._writer = Writer(OutputSettings(output_format=OutputFormat.VIDEO), (MockFilter(
            desired_mode=FilterMode.BY_EVENT), SensorLogs(SensorSettings())))
        return super().setUp()

    def test_output_video(self):
        video_file = decoder.h264_to_mp4('test/data/event_example/clip.h264', 20)
        with open(video_file, 'rb') as f:
            name = self._writer.output_video(f, 0.0, caption=None)
            self.assertIsNot(name, "")
            self.assertTrue(isfile(name + '.mp4'))


class TestsSenderEventModeVideoOutResponse(TestCase):
    def setUp(self):
        #make a sender with a mock url to post to 
        self._sender = Sender(SenderSettings(output_format=OutputFormat.VIDEO), (MockFilter(
            desired_mode=FilterMode.BY_EVENT), SensorLogs(SensorSettings())))
        self._video_file = decoder.h264_to_mp4('test/data/event_example/clip.h264', 20)

   
    @responses.activate
    def test_request_response_video_ok(self):  
        with open(self._video_file, 'rb') as f:
            #mock status response          
            responses.get(
                url=self._sender._server + '/status',
                status=200
            )
            #mock post response
            responses.post(
                url=self._sender._url,
                json={"mock": "response"},
            )
            
            res_post = self._sender.output_video(f, 0.0)
            #check output (expected post response)
            self.assertEqual(res_post['status'],  "sent")
            self.assertEqual(res_post['response'], {"mock":"response"})
    
    @responses.activate
    def test_request_response_video_unhealthy(self):
        #check that when a post is attempted to an unhealthy url, the video is written to disk instead
        with open(self._video_file, 'rb') as f:
            #mock unhealthy status
            responses.get(
                url=self._sender._server + '/status',
                status=401 #I'm unwell! 
            )
            res_post = self._sender.output_video(f, 0.0)
            #check output (expected post response)
            self.assertEqual(res_post['status'], "to_disk")
            self.assertTrue(isfile(res_post['path'] + '.mp4'))

    @responses.activate
    def test_request_response_video_failed_post(self):
        #check that when a failed post is made to the endpoint, the video is written to disk instead
        with open(self._video_file, 'rb') as f:
            #mock healthy status response
            responses.get(
                url=self._sender._server + '/status',
                status=200 #OK 
            )
            #mock post response
            responses.post(
                url=self._sender._url,
                json={"mock": "response"},
                status=401 # I'm unwell!
            )
            res_post = self._sender.output_video(f, 0.0)
            self.assertEqual(res_post['status'], "to_disk")
            self.assertTrue(isfile(res_post['path'] + '.mp4'))


class TestsSenderEventModeStillsOutResponse(TestCase):
    def setUp(self):
        #make a sender with a mock url to post to 
        self._sender = Sender(SenderSettings(output_format=OutputFormat.STILL), (MockFilter(
            desired_mode=FilterMode.BY_EVENT), SensorLogs(SensorSettings())))
        self._stills = decoder.h264_to_jpeg_frames('test/data/event_example/clip.h264')

   
    @responses.activate
    def test_request_response_stills_ok(self):  
        #mock status response          
        responses.get(
            url=self._sender._server + '/status',
            status=200
        )
        #mock post response
        responses.post(
            url=self._sender._url,
            json={"mock": "response"},
        )
        res_post = self._sender.output_group_of_stills(self._stills, 0.0)
        self.assertEqual(res_post['status'], "sent")
        self.assertEqual(res_post['response'], {"mock":"response"})
    
    @responses.activate
    def test_request_response_stills_unhealthy(self):
        #mock status response          
        responses.get(
            url=self._sender._server + '/status',
            status=401 # I'm unwell!
        )
        res_post = self._sender.output_group_of_stills(self._stills, 0.0)
        self.assertEqual(res_post['status'], "to_disk")
    

    @responses.activate
    def test_request_response_stills_failed_post(self):
        #mock healthy status response
        responses.get(
            url=self._sender._server + '/status',
            status=200 #OK 
        )
        #mock post response
        responses.post(
            url=self._sender._url,
            json={"mock": "response"},
            status=401 # I'm unwell!
        )
        res_post = self._sender.output_group_of_stills(self._stills, 0.0)
        self.assertEqual(res_post['status'], "to_disk")






