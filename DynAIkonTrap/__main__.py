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
from distutils.log import Log
from logging import getLogger, basicConfig
import logging
from multiprocessing import Event
from signal import signal, SIGINT
from argparse import ArgumentParser, ArgumentTypeError
from time import sleep
from os.path import exists
from pkg_resources import resource_filename


def main():
    def get_version_number() -> str:
        with open(resource_filename("DynAIkonTrap", "VERSION"), "r") as f:
            version = f.readline().strip()
        return version

    def mp4_file_type(path):
        if not path.endswith(".mp4"):
            raise ArgumentTypeError("Only `.mp4` files allowed")
        if not exists(path):
            raise ArgumentTypeError("This file does not exist. Cannot parse")
        return path


    argparse = ArgumentParser(
        prog="DynAIkonTrap",
        description="An AI-enabled camera trap design targeted at the Raspberry Pi platform",
    )
    argparse.add_argument(
        "--filename", nargs=1, type=mp4_file_type, help="A `.mp4` file to pass to DynAIkonTrap for emulated camera input"
    )
    argparse.add_argument(
        "--version", action="version", version="%(prog)s " + get_version_number()
    )


    args = argparse.parse_args()

    from DynAIkonTrap.camera import Camera
    from DynAIkonTrap.filtering.filtering import Filter
    from DynAIkonTrap.camera_to_disk import CameraToDisk
    from DynAIkonTrap.filtering.remember_from_disk import EventRememberer, EventSynthesisor
    from DynAIkonTrap.comms import Output
    from DynAIkonTrap.sensor import SensorLogs
    from DynAIkonTrap.settings import PipelineVariant, SenderSettings, load_settings
    from DynAIkonTrap.logging import set_logger_config
    from DynAIkonTrap.server.web_serve import ObservationServer
    # Make Ctrl-C quit gracefully
    def handler(signal_num, stack_frame):
        exit(0)

    signal(SIGINT, handler)

    print(
        """
    DynAIkonTrap Copyright (C) 2020 Miklas Riechmann
    This program comes with ABSOLUTELY NO WARRANTY. This is free software, and
    you are welcome to redistribute it under certain conditions. See the
    LICENSE file or <https://www.gnu.org/licenses/> for details.
    """
    )

    print("Welcome to DynAIkon's AI camera trap!")
    print("You can halt execution with <Ctrl>+C anytime\n")


    settings = load_settings()

    # set the logger output file
    set_logger_config(settings.logging.path, settings.logging.level)

    print(
        """
    Logging to: {}
    """.format(
            settings.logging.path
        )
    )

    if args.filename is None:
        if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
            camera = Camera(settings=settings.camera)
            source = camera
        else:
            camera = CameraToDisk(
                camera_settings=settings.camera,
                writer_settings=settings.output,
                filter_settings=settings.filter,
            )
            source = EventRememberer(read_from=camera)
        server = ObservationServer(settings.output, settings.logging, camera)

    else:
        filename = args.filename[0]
        if filename.endswith('.mp4'):
            from vid2frames.Vid2Frames import VideoStream
            vs = VideoStream(filename)
            if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
                source = Camera(settings=settings.camera, read_from=vs)
            else:
                synth = EventSynthesisor(read_from=vs, video_path=filename)
                source = EventRememberer(read_from=synth)
        else:
            print("DynAIkonTrap may only accept video files with the `.mp4` extension at this time.")
            exit(0)

    filters = Filter(read_from=source, settings=settings.filter, sender_settings=settings.output)

    sensor_logs = SensorLogs(settings=settings.sensor)    
    Output(settings=settings.output, read_from=(filters, sensor_logs))



    while True:
        sleep(0.2)
        pass

if __name__ == "__main__":
    main()
