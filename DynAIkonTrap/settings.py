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
The mechanism by which the tunable settings may be loaded into the system. Whilst this may look complicated at first, it provides a simple method to access all of the settings without needing to index into/get from a dictionary. This also means IDEs are able to perform autocompletion and provide type hints as the settings are unpacked in their respective places in the system.

To load the ``settings.json`` file, just run the :func:`load_settings` function once and it returns the a :class:`Settings` object. For example:

.. code:: py

   settings = load_settings()

   camera = DynAIkonTrap.camera.Camera(settings=settings.camera)


The ``settings.json`` should ideally be generated by the provided ``tuner.py`` script, although manual modifications may be desired.

The JSON file should be structured as follows (of course the values can be changed):
```json
{
    "pipeline": {
        "pipeline_variant": 1
    },
    "camera": {
        "framerate": 20,
        "resolution": [
            1920,
            1080
        ]
    },
    "filter": {
        "motion": {
            "small_threshold": 10,
            "sotv_threshold": 5398.984990821726,
            "iir_cutoff_hz": 1.2400793650793651,
            "iir_order": 3,
            "iir_attenuation": 35
        },
        "animal": {
            "animal_threshold": 0.8,
            "detect_humans": true,
            "human_threshold": 0.8,
            "fast_animal_detect": true
        },
        "processing": {
            "smoothing_factor": 0.5,
            "max_sequence_period_s": 10.0,
            "context_length_s": 3.0,
            "detector_fraction": 1.0
        }
    },
    "sensor": {
        "port": "/dev/ttyUSB0",
        "baud": 57600,
        "interval_s": 30.0,
        "obfuscation_distance_km": 2
    },
    "output": {
        "path": "output",
        "output_mode": 0,
        "output_format": 0,
        "output_codec": 0,
        "device_id": 0
    },
    "logging": {
        "level": "INFO",
        "path": "/dev/stdout"
    },
    "version": "1.2.2"
}
```
"""
from json import load, JSONDecodeError
from dataclasses import dataclass
from typing import Tuple, Any, Union
from enum import Enum

from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineVariant(Enum):
    LEGACY = 0
    LOW_POWER = 1


@dataclass
class PipelineSettings:
    """Settings for which video processing pipeline to use"""

    pipeline_variant: PipelineVariant = PipelineVariant.LOW_POWER.value

@dataclass
class CameraSettings:
    """Settings for  :class:`~DynAIkonTrap.camera.Camera` and :class:`~DynAIkonTrap.camera_to_disk.CameraToDisk"""
    framerate: int = 20
    resolution: Tuple[int, int] = (1920, 1080)

@dataclass
class MotionFilterSettings:
    """Settings for a :class:`~DynAIkonTrap.filtering.motion.MotionFilter`"""

    small_threshold: int = 10
    sotv_threshold: float = 5400.0
    iir_cutoff_hz: float = 1.25
    iir_order: int = 3
    iir_attenuation: int = 35


@dataclass
class AnimalFilterSettings:
    """Settings for a :class:`~DynAIkonTrap.filtering.animal.AnimalFilter`"""

    animal_threshold: float = 0.75
    detect_humans: bool = True
    human_threshold: float = 0.75
    fast_animal_detect: bool = True


@dataclass
class ProcessingSettings:
    """Settings for :class:`~DynAIkonTrap.filtering.motion_queue.MotionQueue` and :class:`DynAIkonTrap.filtering.filtering.Filter"""

    smoothing_factor: float = 0.5
    max_sequence_period_s: float = 10.0
    context_length_s: float = 3.0
    detector_fraction: float = 1.0


@dataclass
class SensorSettings:
    """Settings for a :class:`~DynAIkonTrap.sensor.SensorLogs`

    The `obfuscation_distance` should be kept to the range [0..`EARTH_CIRCUMFERENCE_KM/8`), otherwise it will internally be capped to this range. Note that setting to less than 1mm will be rounded down to zero.
    """

    port: str = "/dev/ttyUSB0"
    baud: int = 57600
    interval_s: float = 30.0
    obfuscation_distance_km: float = 2


class OutputFormat(Enum):
    """System output format"""

    VIDEO = 0
    STILL = 1


class OutputMode(Enum):
    """System output mode"""

    DISK = 0
    SEND = 1


class OutputVideoCodec(Enum):
    """System output video codec"""

    H264 = 0
    PIM1 = 1


@dataclass
class OutputSettings:
    device_id: Any = 0
    output_format: OutputFormat = OutputFormat.STILL
    output_mode: OutputMode = OutputMode.DISK
    output_codec: OutputVideoCodec = OutputVideoCodec.H264


@dataclass
class SenderSettings(OutputSettings):
    """Settings for a :class:`~DynAIkonTrap.comms.Sender`"""

    server: str = "https://backend.fastcat-cloud.org/api/v2/spec"
    POST: str = "/predictions/demo"
    userId : str = ""
    apiKey : str = ""



@dataclass
class WriterSettings(OutputSettings):
    """Settings for a :class:`~DynAIkonTrap.comms.Writer`"""

    path: str = "output"


@dataclass
class FilterSettings:
    """Settings for a :class:`~DynAIkonTrap.comms.Filter`"""

    motion: MotionFilterSettings = MotionFilterSettings()
    animal: AnimalFilterSettings = AnimalFilterSettings()
    processing: ProcessingSettings = ProcessingSettings()


@dataclass
class LoggerSettings:
    """Settings for logging"""

    level: str = "INFO"  # Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']
    # `Literal` is not supported in Python from RPi packages, hence no proper type hint
    path: str = "/dev/stdout"  # Default log path is stdout


@dataclass
class Settings:
    """Settings for the camera trap system. A class of nested classes and variables to represent all tunable parameters in the system."""

    pipeline: PipelineSettings = PipelineSettings()
    camera: CameraSettings = CameraSettings()
    filter: FilterSettings = FilterSettings()
    sensor: SensorSettings = SensorSettings()
    output: Union[SenderSettings, WriterSettings] = WriterSettings()
    logging: LoggerSettings = LoggerSettings()


def _version_number() -> str:
    with open("VERSION", "r") as f:
        version = f.readline().strip()
    return version


def load_settings() -> Settings:
    """Call this function once to load the settings from ``settings.json`` file. If the file is not present some defaults are loaded.

    NOTE: these defaults should not be used for anything other than a brief test. Please generate a settings.json for any full deployments (see docs for more info).

    Returns:
        Settings: The settings for all tunable parameters in the system.
    """
    try:
        with open("DynAIkonTrap/settings.json", "rb") as f:
            try:
                settings_json = load(f)
            except JSONDecodeError:
                logger.warning(
                    "Malformed settings.json, using some defaults (JSONDecodeError)"
                )
                return Settings()

            try:
                json_version = settings_json.get("version", "0")
                system_version = _version_number()

                if json_version != system_version:
                    logger.warning(
                        "Running DynAIkonTrap v{}, but settings are for v{}, using defaults".format(
                            system_version, json_version
                        )
                    )
                    return Settings()

                output_mode = OutputMode(
                    settings_json["output"]["output_mode"])
                if output_mode == OutputMode.SEND:
                    output = SenderSettings(
                        server=settings_json["output"]["server"],
                        POST=settings_json["output"]["POST"],
                        device_id=settings_json["output"]["device_id"],
                        output_format=OutputFormat(
                            settings_json["output"]["output_format"]
                        ),
                        output_mode=output_mode,
                        output_codec=OutputVideoCodec(
                            settings_json["output"]["output_codec"]
                        ),
                    )
                else:  # Default to writing to disk
                    output = WriterSettings(
                        device_id=settings_json["output"]["device_id"],
                        output_format=OutputFormat(
                            settings_json["output"]["output_format"]
                        ),
                        output_mode=output_mode,
                        output_codec=OutputVideoCodec(
                            settings_json["output"]["output_codec"]
                        ),
                        path=settings_json["output"]["path"],
                    )

                return Settings(
                    PipelineSettings(**settings_json["pipeline"]),
                    CameraSettings(**settings_json["camera"]),
                    FilterSettings(
                        MotionFilterSettings(
                            **settings_json["filter"]["motion"]),
                        AnimalFilterSettings(
                            **settings_json["filter"]["animal"]),
                        ProcessingSettings(
                            **settings_json["filter"]["processing"]),
                    ),
                    SensorSettings(**settings_json["sensor"]),
                    output,
                    LoggerSettings(**settings_json["logging"]),
                )

            except KeyError as e:
                logger.warning(
                    "Badly formatted settings.json, using defaults (KeyError `{}`)".format(
                        e
                    )
                )
                return Settings()

    except FileNotFoundError:
        logger.warning(
            "The settings.json file could not be found, starting with defaults"
        )
        return Settings()
