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
from json import dump
from types import MappingProxyType

from DynAIkonTrap.settings import (
    OutputMode,
    PipelineVariant,
    SenderSettings,
    Settings,
    FilterSettings,
    OutputFormat,
    OutputSettings,
    load_settings,
    save_settings,
)


def setter(name, setting):
    inpt = input("{} [{}]> ".format(name, setting))
    if inpt != "":
        setting = type(setting)(inpt)
    return setting


def forced_setter(name, setting, value):
    setting = type(setting)(value)
    print("{} [{}]> calculated for you".format(name, setting))
    return setting


def main():

    settings = Settings()

    print(
        """
    DynAIkonTrap Copyright (C) 2020 Miklas Riechmann
    This program comes with ABSOLUTELY NO WARRANTY. This is free software, and
    you are welcome to redistribute it under certain conditions. See the
    LICENSE file or <https://www.gnu.org/licenses/> for details.
    """
    )

    print("Welcome to the tuner!\n")
    print("You will be asked some questions to optimise the camera for your needs.")
    print(
        "For any input prompt enter a value or just hit enter to accept the default (shown in square brackets e.g. [10])."
    )
    print(
        "Lastly, it is recommended not to change any parameters marked with `(ADVANCED)`\n"
    )

    print("Pipeline settings")
    print("---------------")
    pipeline_variant = input(
        "Indicate which pipeline to use LEGACY or LOW_POWER [LOW_POWER]> "
    )
    if pipeline_variant == "LEGACY":
        settings.pipeline.pipeline_variant = PipelineVariant.LEGACY.value
    else:
        settings.pipeline.pipeline_variant = PipelineVariant.LOW_POWER.value

    print("Camera settings")
    print("---------------")
    settings.camera.framerate = setter("framerate", settings.camera.framerate)
    w = setter("Resolution width (ADVANCED)", settings.camera.resolution[0])
    h = setter("Resolution height (ADVANCED)", settings.camera.resolution[1])
    settings.camera.resolution = (w, h)
    # Camera settings for later
    settings.filter.motion.area_reality = setter("Visible animal area to trigger/m^2", settings.filter.motion.area_reality)
    settings.filter.motion.subject_distance = setter("Expected distance of animal from sensor/m", settings.filter.motion.subject_distance)
    settings.filter.motion.animal_speed = setter("Min. animal trigger speed/m/s", settings.filter.motion.animal_speed)
    settings.filter.motion.focal_len = setter("Camera focal length/m (ADVANCED)", settings.filter.motion.focal_len)
    settings.filter.motion.pixel_size = setter("Pixel size/m (ADVANCED)", settings.filter.motion.pixel_size)
    settings.filter.motion.num_pixels = setter("Number of pixels on sensor (width) (ADVANCED)", settings.filter.motion.num_pixels)
    settings.filter.motion.update(settings.camera)

    print("\nFilter settings")
    print("---------------")
    print("----Motion filtering")
    settings.filter.motion.small_threshold = setter(
        "SoTV small movement threshold", settings.filter.motion.small_threshold
    )


    settings.filter.motion.sotv_threshold = forced_setter(
        "SoTV general threshold",
        settings.filter.motion.sotv_threshold,
        settings.filter.motion.sotv_threshold
    )
    settings.filter.motion.iir_cutoff_hz = forced_setter(
        "SoTV smoothing cut-off frequency/Hz",
        settings.filter.motion.iir_cutoff_hz,
        settings.filter.motion.iir_cutoff_hz
    )
    settings.filter.motion.iir_order = setter(
        "SoTV smoothing IIR order (ADVANCED)", settings.filter.motion.iir_order
    )
    settings.filter.motion.iir_attenuation = setter(
        "SoTV smoothing IIR stop-band attenuation (ADVANCED)",
        settings.filter.motion.iir_attenuation,
    )

    print("----Animal filtering")

    settings.filter.animal.animal_threshold = setter(
        "Animal confidence threshold (ADVANCED)", settings.filter.animal.animal_threshold
    )
    animal_fcc = input("Would you like to use FASTCAT-Cloud for animal detections? (requires an internet connection) (y/n) [n] > ")
    if animal_fcc == "y":
        settings.filter.animal.fastcat_cloud_detect = True
    else:
        detect_humans = input(
            "Would you like DynAIkonTrap to also attempt to filter out humans from detections? YES or NO [YES]> "
        )
        if detect_humans == "NO":
            settings.filter.animal.detect_humans = False
        else:
            settings.filter.animal.detect_humans = True
            settings.filter.animal.human_threshold = setter(
                "Human confidence threshold (ADVANCED)", settings.filter.animal.human_threshold
            )
        faster_detector = input(
            "Would you like DynAIkonTrap to use a faster, but less accurate detector (YES) or slower and more accurate (NO)? YES or NO [YES]> "
        )
        if faster_detector == "NO":
            settings.filter.animal.fast_animal_detect = False
        else:
            settings.filter.animal.fast_animal_detect = True
            
    print("----Processing settings")
    if settings.pipeline.pipeline_variant == PipelineVariant.LEGACY.value:
        settings.filter.processing.smoothing_factor = forced_setter(
            "Smoothing factor",
            settings.filter.processing.smoothing_factor,
            1.0 / settings.filter.motion.iir_cutoff_hz,
        )
    settings.filter.processing.max_sequence_period_s = setter(
        "Max. motion sequence period/s (ADVANCED)",
        settings.filter.processing.max_sequence_period_s,
    )
    settings.filter.processing.context_length_s = setter(
        "Motion context buffer length/s",
        settings.filter.processing.context_length_s,
    )
    if settings.pipeline.pipeline_variant == PipelineVariant.LOW_POWER.value:
        settings.filter.processing.detector_fraction = setter(
            "Fraction of event to process with neural network, range: [0-1]",
            settings.filter.processing.detector_fraction,
        )

    print("\nSensor settings")
    print("---------------")
    settings.sensor.port = setter("Sensor board port", settings.sensor.port)
    settings.sensor.baud = setter("Sensor board baud rate", settings.sensor.baud)
    settings.sensor.interval_s = setter(
        "Sensor reading interval/s", settings.sensor.interval_s
    )
    settings.sensor.obfuscation_distance_km = setter(
        "GPS obfuscation distance/km", settings.sensor.obfuscation_distance_km
    )

    print("\nOutput settings")
    print("---------------")
    mode = input("Output mode: save to disk, or upload to server? (d/s) [d]> ")
    if mode == "s":
        settings.output = SenderSettings
        settings.output.output_mode = OutputMode.SEND.value
        fcc = input("Would you like to upload your observations to FASTCAT-cloud? (y/n) [y]> ")
        if fcc == "n":
            settings.output.is_fcc = False
            settings.output.server = input("Please input your own server address > ")
            settings.output.POST   = input("Please input your own server POST endpoint > ")        
        else:
            settings.output.is_fcc = True
            settings.output.server = setter("Current FASTCAT-cloud backend address", settings.output.server)
            settings.output.POST = setter("Current FASTCAT-cloud API POST endpoint", settings.output.POST)
            settings.output.userId = input("Please input your FASTCAT-Cloud User ID > ")
            settings.output.apiKey = input("Please input your FASTCAT-Cloud API key > ")
    else:
        settings.output = OutputSettings
        settings.output.output_mode = OutputMode.DISK.value
    settings.output.path = setter("Output path", settings.output.path)


    format = input("Output format video? (y/n) [y]> ")
    if format == "n":
        settings.output.output_format = OutputFormat.STILL.value
    else:
        settings.output.output_format = OutputFormat.VIDEO.value

    settings.output.device_id = setter("Device ID", settings.output.device_id)
    if settings.pipeline.pipeline_variant == PipelineVariant.LOW_POWER.value:
        meta = input("Delete disk metadata after detections made? (y/n) [y]> ")
        if meta == "n":
            settings.output.delete_metadata = False
        else: 
            settings.output.delete_metadata = True

    print("\nLogging settings")
    print("---------------")
    settings.logging.level = setter(
        "Level from `DEBUG`, `INFO`, `WARNING`, `ERROR`", settings.logging.level
    )
    settings.logging.path = setter(
        "Logger output file, defaults to stdout", settings.logging.path
    )

    save_settings(settings)


if __name__ == "__main__":
    main()
