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
An interface for writing animal frames to disk or sending them to a server. The ``AbstractOutput`` combines a frame(s) with the most appropriate sensor log(s) and outputs these.
"""
from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
from dataclasses import dataclass
from fileinput import filename
from queue import Queue
import json
from multiprocessing import Process, Queue
from typing import Dict, IO, Tuple, List, Union
from tempfile import NamedTemporaryFile
from io import StringIO
from datetime import datetime, timezone
from pathlib import Path
from os import listdir, nice, makedirs
from os.path import join, splitext, exists
from json import dump, dumps
from shutil import move
from glob import glob

from requests import RequestException, post, get, head
from requests.exceptions import HTTPError, ConnectionError
from numpy import asarray
import cv2
from DynAIkonTrap.filtering.event import EventProcessor  # pdoc3 can't handle importing individual OpenCV functions

from DynAIkonTrap.filtering.filtering import Filter, FilterMode
from DynAIkonTrap.filtering.remember_from_disk import EventData
from DynAIkonTrap.imdecode import decoder
from DynAIkonTrap.sensor import SensorLog, SensorLogs, Reading
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import (
    OutputMode,
    SenderSettings,
    OutputFormat,
    OutputSettings,
)

logger = get_logger(__name__)


class VideoCaption:
    """Class to aid in generating captions for video output. The captions are based on the logged sensor readings."""

    def __init__(self, sensor_logs: SensorLogs, framerate: float):
        """
        Args:
            sensor_logs (SensorLogs): The object containing the log of sensor readings
            framerate (float): Camera framerate
        """
        self._sensor_logs = sensor_logs
        self._framerate = framerate

    def _generate_captions_dict(self, timestamps: List[float]) -> Dict:
        """NOTE: If sensor readings do not line up with frame capturing, there may be slight off-by-one style errors."""
        captions = {}
        for frame_number, timestamp in enumerate(timestamps):
            # Retrieve the corresponding log
            log = self._sensor_logs.get(timestamp)

            # Get existing or create new caption with this log
            key = int(
                frame_number // (self._framerate *
                                 self._sensor_logs.read_interval)
            )
            caption = captions.get(
                key,
                {
                    "start": frame_number,
                    "stop": frame_number,
                    "log": log,
                },
            )

            # Extend caption duration for a subsequent frame using the same log
            caption["stop"] += 1

            captions.update({key: caption})
        return captions

    def _video_time_to_str(self, video_time: float) -> str:
        ss = int(video_time % 60)
        ttt = (video_time % 60 - ss) * 1000
        mm = video_time // 60
        return "{:02.0f}:{:02.0f}.{:03.0f}".format(mm, ss, ttt)

    def _reading_to_str(self, reading: Reading) -> str:
        if reading is None:
            return "?"
        return "{x.value}{x.units}".format(x=reading)

    def _captions_dict_to_vtt(self, captions: Dict, framerate: float) -> str:
        vtt = "WEBVTT \n"
        vtt += "\n"

        for key, caption in sorted(captions.items()):
            log: SensorLog = caption["log"]
            if log is None:
                continue

            start_time = caption["start"] / framerate
            stop_time = caption["stop"] / framerate

            vtt += "{} --> {} - Sensor@{}\n".format(
                self._video_time_to_str(start_time),
                self._video_time_to_str(stop_time),
                "{:%H:%M:%S}".format(
                    datetime.fromtimestamp(log.system_time, timezone.utc)
                ),
            )

            vtt += "T: {} - RH: {} - L: {} - P: {}\n\n".format(
                self._reading_to_str(log.readings.get("SKEW_TEMPERATURE")),
                self._reading_to_str(log.readings.get("HUMIDITY")),
                self._reading_to_str(log.readings.get("BRIGHTNESS")),
                self._reading_to_str(log.readings.get("ATMOSPHERIC_PRESSURE")),
            )
        return vtt

    def generate_vtt_for(self, timestamps: List[float]) -> StringIO:
        """Generate WebVTT captions containing the sensor readings at given moments in time.

        Args:
            timestamps (List[float]): Timestamps for every frame in the motion/animal sequence

        Returns:
            StringIO: The WebVTT captions ready to be sent to a server
        """
        captions = self._generate_captions_dict(timestamps)
        return StringIO(self._captions_dict_to_vtt(captions, self._framerate))

    def generate_sensor_json(self, timestamps: List[float]) -> StringIO:
        """Generate JSON captions containing the sensor readings at given moments in time.

        The format is as follows:

        .. code:: json

           [
               {
                   "start": 0,
                   "end": 1,
                   "log": {
                       "EXAMPLE_SENSOR_1": {
                           "value": 0.0,
                           "units": "x"
                       },
                       "EXAMPLE_SENSOR_2": {
                           "value": 0.0,
                           "units": "x"
                       }
                   }
               },
               {
                   "start": 1,
                   "end": 5,
                   "logs": {}
               }
           ]


        The ``"start"`` and ``"end"`` correspond to the frame numbers in which the sensor logs are valid. The frame numbers are inclusive. It is not guaranteed that all frames are covered by logs. There may also be also be overlaps between entries if the exact timestamp where a new set of sensor readings becomes valid occurs during a frame.

        Args:
            timestamps (List[float]): Timestamps for every frame in the motion/animal sequence

        Returns:
            StringIO: The JSON captions wrapped in a :class:`StringIO`, ready for writing to file
        """
        captions = self._generate_captions_dict(timestamps)
        logger.debug(captions)

        json_captions = []
        for c in captions.values():
            log = c["log"]
            if log != None:
                json_captions.append(
                    {"start": c["start"], "end": c["stop"],
                        "log": log.serialise()}
                )
        return StringIO(dumps(json_captions))


class AbstractOutput(metaclass=ABCMeta):
    """A base class to use for outputting captured images or videos. The :func:`output_still` and :func:`output_video` functions should be overridden with output method-specific implementations."""

    def __init__(self, settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]):
        self._animal_queue = read_from[0]
        self._sensor_logs = read_from[1]
        self.framerate = self._animal_queue.framerate
        self._delete_metadata = settings.delete_metadata
        self._video_suffix = ".mp4"

        if settings.output_format == OutputFormat.VIDEO.value:
            if self._animal_queue.mode == FilterMode.BY_FRAME:
                self._reader = Process(
                    target=self._read_frames_to_video, daemon=True)
            elif self._animal_queue.mode == FilterMode.BY_EVENT:
                self._reader = Process(
                    target=self._read_events_to_video, daemon=True)

        elif settings.output_format == OutputFormat.STILL.value:
            if self._animal_queue.mode == FilterMode.BY_FRAME:
                self._reader = Process(
                    target=self._read_frames_to_image, daemon=True)
            elif self._animal_queue.mode == FilterMode.BY_EVENT:
                self._reader = Process(
                    target=self._read_events_to_image, daemon=True)

        self._reader.start()

    def close(self):
        self._reader.terminate()
        self._reader.join()

    def _read_frames_to_image(self):
        while True:
            frame = self._animal_queue.get()
            if frame is None:
                continue

            log = self._sensor_logs.get(frame.timestamp)
            if log is None:
                logger.warning("No sensor readings")
                self.output_still(image=frame.image, time=frame.timestamp)
            else:
                self.output_still(
                    image=frame.image, time=frame.timestamp, sensor_log=log
                )

    def _read_frames_to_video(self):
        start_new = True
        start_time = 0
        caption_generator = VideoCaption(self._sensor_logs, self.framerate)
        while True:
            frame = self._animal_queue.get()

            # End of motion sequence
            if frame is None and not start_new:
                start_new = True
                writer.release()
                captions = caption_generator.generate_sensor_json(
                    frame_timestamps)
                self.output_video(
                    video=file, time=start_time, caption=captions)
                continue

            decoded_image = cv2.imdecode(
                asarray(frame.image), cv2.IMREAD_COLOR)

            # Start of motion sequence
            if start_new:
                start_new = False
                start_time = frame.timestamp
                frame_timestamps = []

                file = NamedTemporaryFile(suffix=self._video_suffix, delete=False)
                writer = cv2.VideoWriter(
                    file.name,
                    cv2.VideoWriter_fourcc(*'mp4v'),
                    self.framerate,
                    (decoded_image.shape[1], decoded_image.shape[0]),
                )

            writer.write(decoded_image)
            frame_timestamps.append(frame.timestamp)

    def _read_events_to_video(self):
        nice(4)
        caption_generator = VideoCaption(self._sensor_logs, self.framerate)
        while True:
            try:
                event = self._animal_queue.get()
                globbed = glob(join(event.dir, 'clip.h264')) + glob(join(event.dir, 'clip.mp4'))
                encoded_video_file = globbed[0]
                filename = decoder.h264_to_mp4(encoded_video_file, self.framerate, self._video_suffix)
                caption = caption_generator.generate_sensor_json(
                    [event.start_timestamp]
                )
                with open(filename, 'rb') as file:
                    self.output_video(
                        video=file, time=event.start_timestamp, caption=caption
                    )
                if self._delete_metadata:
                    EventProcessor.delete_event(event)

            except Exception as e:
                logger.error("Event to video error! Error: {}".format(e))
                pass

    def _read_events_to_image(self):
        nice(4)
        while True:
            try:
                event = self._animal_queue.get()
                log = self._sensor_logs.get(event.start_timestamp)
                if log is None:
                   logger.warning("No sensor readings for event captured at time: {}".format(datetime.fromtimestamp(event.start_timestamp)))
                globbed = glob(join(event.dir, 'clip.h264')) + glob(join(event.dir, 'clip.mp4'))
                encoded_video_file = globbed[0]
                images = decoder.h264_to_jpeg_frames(encoded_video_file)
                self.output_group_of_stills(
                        images=images, time=event.start_timestamp, sensor_log=log
                    )
                if self._delete_metadata:
                    EventProcessor.delete_event(event)
            except Exception as e:
                logger.error("Event to images error! Error: {}".format(e))
    

    @abstractmethod
    def output_still(self, image: bytes, time: float, sensor_log: SensorLog):
        """Output a still image with its sensor data. The sensor data can be provided via the keyword arguments.

        Args:
            image (bytes): The image  
            time (float): UNIX timestamp when the image was captured
            sensor_log (SensorLog): Log of sensor values at time frame was captured
        """
        pass
    
    @abstractmethod
    def output_group_of_stills(self, images: List[str], time: float, sensor_log: SensorLog):
        """Output a group of still images all correlated with one-and-other, eg in an event. The sensor data can be provided via the keyword arguments.

        Args:
            images (List[bytes]): A list of images saved on disk
            time (float): UNIX time stamp when the images were captured
            sensor_log (SensorLog): Log of sensor values at the time the frames were captured
        """
        pass

    @abstractmethod
    def output_video(self, video: IO[bytes], time: float, caption: StringIO = None, **kwargs):
        """Output a video with its meta-data. The sensor data is provided via the video captions (``caption``).

        Args:
            video (IO[bytes]): MP4 video 
            caption (StringIO): Caption of sensor readings as produced by :func:`VideoCaption.generate_sensor_json()`
            time (float): UNIX timestamp when the image was captured
        """
        pass


class Writer(AbstractOutput):
    def __init__(self, settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]):

        path = Path(settings.path).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        self._path = path.resolve()
        super().__init__(settings, read_from)
        logger.debug("Writer started (format: {})".format(
            settings.output_format))

    def _unique_name(self, capture_time: float) -> str:

        # Get all filenames and remove extensions
        names = map(lambda x: x[0], map(
            lambda x: x.split("."), listdir(self._path)))

        # Base the new file's name on the capture time
        name = "{:%Y-%m-%d_%H-%M-%S-%f}".format(
            datetime.fromtimestamp(capture_time, timezone.utc)
        )
        counter = 0

        # If the name is already taken try adding a number
        while "{}_{}".format(name, counter) in list(names):
            counter += 1

        name = "{}_{}".format(name, counter)

        return join(self._path, name)

    def output_still(self, image: bytes, time: float, sensor_log: SensorLog=None):

        name = self._unique_name(time)

        with open(name + ".jpg", "wb") as f:
            f.write(image)
        if sensor_log is not None:
            with open(name + ".json", "w") as f:
                dump(sensor_log.serialise(), f)

        logger.info("Image and meta-data saved")
    
    def output_group_of_stills(self, images: List[str], time: float, sensor_log: SensorLog=None) -> str:
        """A function to output a group of correlated still images under one directory. E.G. Frames in a video. Takes a list of paths to correlated frames and a time. A directory is constructed from the time given, images within the directory are saved in list-order in the form dir_name/cap0.jpg, dir_name/cap1.jpg ... 
        If a sensor log is given, this is saved within the directory in json format with a filename constructed from the given timestamp. 
        The directory name where everything is saved is returned in string format.

        Args:
            images (List[str]): List of correlated images to save in common detection directory
            time (float): Time stamp to associate with this detection
            sensor_log (SensorLog): The sensor log associated with this detection, can be None 

        Returns:
            str: Directory name containing sensor log and/or saved images, given as a string
        """
        dir_name = self._unique_name(time)
        if not exists(dir_name):
            makedirs(dir_name)
        for count, image in enumerate(images):
            extension = splitext(image)[1]
            move(image, dir_name + '/cap' + str(count) + extension)

        if sensor_log is not None:
            with open("{}/{}.json".format(dir_name, datetime.fromtimestamp(time)), "w") as f:
                dump(sensor_log.serialise(), f)

        logger.info("Group of images saved")
        return dir_name



    def output_video(self, video: IO[bytes], time: float, caption: StringIO = None, **kwargs) -> str:
        """Takes a video file bytestream and saves to disk alongside an optional caption file with the same name with a .json extension. These names are set with a timestamp.

        Args:
            video (IO[bytes]): The video file to be saved
            time (float): The time corresponding to this video 
            caption (StringIO): The caption to be saved, can be None to save no caption file
         Returns:
            str: File path (excluding extension) for the caption file and/or saved video
        """
        name = self._unique_name(time)
        video.close()
        move(video.name, name + self._video_suffix)
        if caption is not None:
            with open(name + ".json", "w") as f:
                f.write(caption.getvalue())

        logger.info("Video and caption saved")
        return name


class Sender(Writer):
    """The Sender is a simple interface for sending the desired data to a server. Inherits from :class:`~DynAIkonTrap.comms.Writer`, if server posts fail, Writer methods are called instead to save data on disk."""

    def __init__(self, settings: SenderSettings, read_from: Tuple[Filter, SensorLogs]):
        self._server = settings.server
        self._device_id = settings.device_id
        self._path_POST = settings.POST
        self._is_fcc = settings.is_fcc
        self._sender_log = SenderLog(settings)
        #form url for post
        if settings.is_fcc:
            self._url = self._server + self._path_POST + '?userId=' + \
                    settings.userId + '&apiKey=' + settings.apiKey
        else:
            self._url = self._server + self._path_POST
        super().__init__(settings, read_from)

        logger.debug("Sender started (format: {})".format(
            settings.output_format))

    def check_health(self) -> bool:
        """Checks health of the server to send to

        Returns:
            bool: returns True if connection deemed healthy, False otherwise
        """
        try:
            if self._is_fcc:
                result = get(self._server + "/status")
            else: 
                result = head(self._server)
                result.raise_for_status()
            return result.status_code == 200
            
        except ConnectionError as e:
            logger.error("Connection error to server for uploads: {}".format(e))
            return False
        except HTTPError as e:
            logger.error("HTTP error to server for uploads: {}".format(e))
            return False
        except RequestException as e: 
            logger.error("Requests error to server for uploads: {}".format(e))
            return False



    def output_still(self, image: bytes, time: float, sensor_log: SensorLog=None):
        healthy = self.check_health()
        send_failure = False
        if healthy:
            image_filename = image.name
            files_arr = [('image', (image_filename, image, 'image/jpeg'))]
            logger.info("Sending detection (image) to server with url: {}".format(self._url))
            try:
                meta = {"trap_id": self._device_id}
                if sensor_log is not None:
                    meta.update(sensor_log.serialise())
                r = post(self._url,
                        data=meta, files=files_arr)
                r.raise_for_status()
                logger.info("Image sent")
                ret = {"status":"sent"}
                ret.update({"response":r.json()})
                self._sender_log.log(ret)
                return ret
            except HTTPError as e:
                logger.error("HTTP error while sending detection: {}".format(e))
                send_failure = True
            except ConnectionError as e:
                logger.error("Connection error while sending detection: {}".format(e))
                send_failure = True
            except RequestException as e:
                logger.error("Requests error while sending detection: {}".format(e))
                send_failure = True
            
        if not healthy or send_failure:
            logger.info("Connection to server down. Send cancelled, writing detection to disk instead.")
            filename = super().output_still(image, time, sensor_log)
            ret = {"status":"to_disk", "path":filename}
            self._sender_log.log(ret)
            return ret

    def output_group_of_stills(self, images: List[str], time: float, sensor_log: SensorLog=None):
        healthy = self.check_health()
        send_failure = False
        if healthy:
            logger.info("Sending detection (images group) to server with url: {}".format(self._url))
            try:
                meta = {"trap_id": self._device_id}
                if sensor_log is not None:
                    meta.update(sensor_log.serialise())
                files_l = []
                file_handles = []
                for filename in images:
                    f = open(filename, 'rb')
                    files_l.append(('image', (filename, f, 'image/jpeg')))
                    file_handles.append(f)
                r = post(self._url, data=meta, files=files_l)
                r.raise_for_status()
                logger.info("Images sent")
                ret = {"status":"sent"}
                ret.update({"response":r.json()})
                self._sender_log.log(ret)
                return ret
            except HTTPError as e:
                logger.error("HTTP error while sending detection: {}".format(e))
                send_failure = True
            except ConnectionError as e:
                logger.error("Connection error while sending detection: {}".format(e))
                send_failure = True
            except RequestException as e:
                logger.error("Requests error while sending detection: {}".format(e))
                send_failure = True
            finally:
                for file in file_handles:
                    file.close()
        if not healthy or send_failure:
            logger.info("Connection to server down. Send cancelled, writing detection to disk instead.")
            dir_name = super().output_group_of_stills(images, time, sensor_log)
            ret = { "status":"to_disk", "path":dir_name}
            self._sender_log.log(ret)
            return ret

    def output_video(self, video: IO[bytes], time: float, caption: StringIO = None,  **kwargs) -> Dict:
        """A function post a video clip to the sender's url. The video caption and timestamp are included in the post data. If a problem arises with the connection, the video will be saved to disk instead using the inherited Writer

        Args:
            video (IO[bytes]): The video file to post to server
            time (float): The time stamp associated with the video capture
            caption (StringIO, optional): The optional video caption. Defaults to None.

        Returns:
            str: If the post attempt was sucessful, returns an empty string. Otherwise, returns the string output of :func:`~DynAIkonTrap.comms.Writer.output_video`
        """
        healthy = self.check_health()
        send_failure = False
        if healthy:
            meta = {"trap_id": self._device_id, "time": time}
            video_filename = video.name
            files_arr = [('image', (video_filename, video, 'video/mp4'))]
            logger.info("Sending detection (video) to server with url: {}".format(self._url))
            try:
                r = post(self._url, data=meta, files=files_arr)
                r.raise_for_status()
                logger.info("Video sent")
                ret = {"status":"sent"}
                ret.update({"response":r.json()})
                self._sender_log.log(ret)
                return ret
            except HTTPError as e:
                logger.error("HTTP error while sending detection: {}".format(e))
                send_failure = True
            except ConnectionError as e:
                logger.error("Connection error while sending detection: {}".format(e))
                send_failure = True
            except RequestException as e:
                logger.error("Requests error while sending detection: {}".format(e))
                send_failure = True
        if not healthy or send_failure:
            logger.info("Connection to server down. Send cancelled, writing detection to disk instead.")
            filename = super().output_video(video, time, caption)
            ret = { "status":"to_disk", "path":filename}
            self._sender_log.log(ret)
            return ret

class SenderLog:
    """A class to keep a log about detections sent to remote servers, useful to record observation IDs from FASTCAT-Cloud"""
    def __init__(self, settings: SenderSettings):
        self._filename = settings.path + "/output_log.txt"
    
    def log(self, result: Dict):
        """Logs a sender result to the log file

        Args:
            result (str): sender result from accessing server or saving to disk  
        """
        with open(self._filename, 'a') as f:
            if result["status"] == "to_disk":
                f.write("Detection written to disk at path: {}\n".format(str(result["path"])) )
            elif result["status"] == "sent":
                f.write("Detection sent to the server, response: {}\n".format(str(result["response"])))


def Output(
    settings: OutputSettings, read_from: Tuple[Filter, SensorLogs]
) -> Union[Sender, Writer]:
    """Generator function to provide an implementation of the :class:`~AbstractOutput` based on the :class:`~DynAIkonTrap.settings.OutputMode` of the ``settings`` argument. If the output mode is SEND, this function performs some error checking/handling before configuring a :class:`~DynAIkonTrap.comms.Sender` instance"""
    if settings.output_mode == OutputMode.SEND.value:
        # check a few things before we configure the sender...
        sender_config_failure = False
        try:
            #check server is available
            if settings.is_fcc:
                #check api health
                logger.info("Connecting to FASTCAT-Cloud at: {} ...".format(settings.server))
                result = get(settings.server + "/status")
                result.raise_for_status()
                if result.status_code == 200:
                    logger.info("Successful connection to URL: {}".format(settings.server))
                     #check the api key and user ids have been set
                    if settings.apiKey == "" or settings.userId == "":
                        logger.error("User ID / API Key not set. Cannot authenticate FASTCAT-Cloud")
                        sender_config_failure = True
                    # check the user can authenticate FCC with credentials 
                    else:
                        logger.info("Checking FASTCAT-Cloud authentication with User ID: {} and API Key: {} ...".format(settings.userId, settings.apiKey))
                        result = get(settings.server + "/api/v2/authentication/user?userId=" + settings.userId + "&apiKey=" + settings.apiKey)
                        if result.status_code == 200:
                            user = result.json()
                            logger.info("Success! Authenticated as: {} with Email: {}".format(user["body"]["user"]["Name"], user["body"]["user"]["Email"]))
                            Sender(settings=settings, read_from=read_from)
                        else: 
                            logger.error("Cannot authenticate with FASTCAT-Cloud. Error message from server: {}".format(result.json()["message"]))
                            sender_config_failure = True
                else:
                    logger.error("Problem accessing FASTCAT-Cloud API. HTTPError: {}".format(result.raise_for_status()))
                    sender_config_failure = True
            else:
                #check url is accessible
                logger.info("Connecting to user's server at: {} ...".format(settings.server))
                result = head(settings.server)
                if result.status_code == 200:
                    logger.info("Successful connection to URL: {}".format(settings.server))
                    Sender(settings=settings, read_from=read_from)

                else:
                    logger.error("Problem connecting to the user's server. HTTPError: {}".format(result.raise_for_status()))
                    sender_config_failure = True
        except AttributeError as e:
            logger.error(
                "Attribute error raised when trying to check the SenderSettings: {}.".format(e)
            )
            sender_config_failure = True
        except ConnectionError as e:
            logger.error("Connection error. Server address: {}, are you sure this is correct? Error message: {}".format(settings.server, e))
            sender_config_failure = True
        except RequestException as e:
            logger.error(
                "Requests error: {}".format(e)
            )
            sender_config_failure = True
        if sender_config_failure:
            logger.info(
                "Couldn't initialise Sender, continuing with a Writer instead."
            )
            Writer(settings=settings, read_from=read_from)
    else:
        Writer(settings=settings, read_from=read_from)
