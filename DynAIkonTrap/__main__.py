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
from argparse import ArgumentParser, ArgumentTypeError, RawDescriptionHelpFormatter
from textwrap import dedent
from time import sleep
from os.path import exists, abspath, basename
from os import makedirs, remove
from pkg_resources import resource_filename
from subprocess import run


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
        formatter_class=RawDescriptionHelpFormatter,
        description=dedent("""\
        An AI-enabled camera trap design targeted at the Raspberry Pi
        platform.

        Read our documentation at https://dynaikon.com/trap-docs

        The camera trap can be operated in a 'live mode' and 'emulated mode'.

        LIVE MODE
        ---------
        Use the on-board camera to perform real-time animal detections.

        EMULATED MODE
        -------------
        Takes a pre-recorded `.mp4` file and filters it using our AI video
        pipeline.

        Caveat for 'emulated mode': the video files need to be pre-processed to
        a special format. DynAIkonTrap can do this, see the options

            --keep
            --skip-preprocess

        for handling this preprocessing.
        """),
    )
    argparse.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + get_version_number()
    )
    argparse.add_argument(
        "--filename",
        type=mp4_file_type,
        help="(Emulated mode) A `.mp4` file to pass to DynAIkonTrap for "
             "emulated camera input"
    )
    argparse.add_argument(
        "--keep", "-k",
        action="store_true",
        help="(Emulated mode) Keep preprocessed video files after "
             "completion, defaults to False. "
             "(Source files are never deleted). "
             "Useful when wants to re-run the pipeline on the same file with "
             "different tuning parameters",
        default=False
    )
    argparse.add_argument(
        "--skip-preprocess", "-s",
        action="store_true",
        help="(Emulated mode) Do not preprocess video files, "
             "defaults to False. This is useful in cases when the video "
             "files have already been preprocessed. Implies --keep.",
        default=False
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
        filename = args.filename
        if not filename.endswith('.mp4'):
            print("DynAIkonTrap may only accept video files with the `.mp4` extension at this time.")
            exit(0)

        if args.skip_preprocess:
            args.keep = True
            processed = abspath(args.filename)

        else:
            makedirs(settings.output.path, exist_ok=True)
            processed = abspath(f'{settings.output.path}/{basename(args.filename)}.processed.mp4')

            print("Preparing video file...")
            ffmpeg = run(['ffmpeg', '-i', args.filename, '-c:v', 'mpeg4',
                          '-q:v', '1', '-an', processed], capture_output=True)

            if ffmpeg.returncode != 0:
                print(ffmpeg.stdout.decode("utf-8"))
                print(ffmpeg.stderr.decode("utf-8"))
                exit(1)

            print("[Done] Preparing video file (ffmpeg)")

        from Vid2Frames.Vid2Frames import VideoStream
        vs = VideoStream(processed)
        if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
            source = Camera(settings=settings.camera, read_from=vs)
        else:
            synth = EventSynthesisor(read_from=vs, video_path=processed)
            source = EventRememberer(read_from=synth)

    filters = Filter(read_from=source, settings=settings.filter, sender_settings=settings.output)

    sensor_logs = SensorLogs(settings=settings.sensor)    
    Output(settings=settings.output, read_from=(filters, sensor_logs))



    while True:
        sleep(0.2)
        pass

    # This code will not run, it is behind a while True statement,
    # However, it is here as a placeholder until multithreading is more
    # robustly handled
    if not args.keep:
        remove(processed)

if __name__ == "__main__":
    main()
