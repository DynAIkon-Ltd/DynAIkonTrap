# Change Log
## [v1.5.1] - 2022-11-14

### Fixed
- Fixed legacy pipeline not emptying sequences, `get_highest_priority` checks for frames with priority < 0 after labelling. 
    - See lines 195 - 206 in `motion_queue.py`

## [v1.5.0] - 2022-10-21

### Added
- Web server to aid with user experience and setup.
- Features
    - Home page with scalable graphics for mobile and desktop machines
    - Dedicated page to check camera FOV and video feed
    - Nested HTML to browse and serve observations
    - Page to view and serve the system log
    - Page to access the terminal via shellinabox
- Files
    - `DynAIkonTrap.server.web_serve.py` handles management of the http server and shellinabox daemon
    - `DynAIkonTrap.server.html_generator.py` handles generation of the html pages 
    - `html/` directory created to house some html
    - `assets/` directory contains downloaded style sheets for bootstrap, thus styling can be used offline

## [v1.4.5] - 2022-09-12
### Fixed 
- Removed output switching in `settings.py` `load_settings()` function
- Added dims argument to `imdecode.yuv_to_png_temp_file`, updated `animal.py` 
- Updated settings loader to assign value to `delete_metadata`
- syntax error in comms.py self.server -> self._server
- YUV decoding error for dyntrap camera mode see commit: 517b716fe0606824461b1e7a8d22e7980f85f61f
- Legacy mode camera crash, cannot find bitrate - fixed. See commit: 490d425d2e6bfe6ee316c24d33c277137de604ef

### Added 
- Added details in `tuning.rst` to run the tuner. Future expansion required for a user guide for the tuner.
- methods to `settings.py` which allow settings to be loaded, modified and queried via a bash interface and anywhere in the program
- update method to motion settings
    - important motion parameters are now no longer computed in `tuner.py`, instead they are computed within the MotionSettings class itself via an `update` method. This has been nessessary to make these settings portable and also makes the computation of motion parameters part of the dynaikontrap package.
- more fields to motion settings, making it more portable 
- a bash whipper TUI to configure settings: `dyntrap-config.sh`
    - this replaces the need to call `tuner.py` to configure setttings and provides a more user-friendly method to setup the camera trap parameters. 
    - this is also callable from anywhere on the system using the command `dyntrap-config` after `setup.sh` has been run
### Changed 
- The YUV format was: dim,dim,imagedata,dim,dim,imagedata it is now a single pair of dimensions at the start of the file, all image data in the stream is assumed to be of the same size.
## [v1.4.0] - 2022-08-12
### Fixed
- Logger now sets the level appropriately
- Removed output codec selection fom `settings.py`. The ability to select between codecs was thought to be justified by different codecs available on different devices. Instead, selecting the fourcc encoder `mp4v` works on all devices which support h264 encoding. No need for this setting.
- Output stage bug fixed in `comms.py` for moving temporary file to output directory
- The YUV file format modification is a breaking change to the `yuv_buf_to_bgr_array` within `imdecode.py` 
    - This function is modified to read the frame dimensions from file and decode the remainder of the YUV buffer
- The `h264_to_mp4` method within `imdecode.py` is updated to use the `-r` argument when calling `ffmpeg`. This is in the place of the `-framerate` flag which is depreciated. 

### Added 
- Docs explaining how to run the camera trap on a simulated video input in `running.rst`. 
- Some logging messages added in `remember_from_disk.py`, changed verbosity of log messages in `filtering.py` and `event.py`
- Within `__main__.py` a CLI is written to allow the passing of filenames, appropriate argument parsing is included to ensure a `.mp4` file is passed and that file exists. If no file is passed, the Vid2Frames library is not imported, thus DynAIkonTrap can function as normal if vid2frames is not installed. 
- Within `comms.py`, the functions `_read_events_to_image` and `_read_events_to_video` are modified to work with `.mp4` files as well as `.h264`. This is a basic change implemented using glob. Allows for easier integration with `Vid2Frames`
- `imdecode.py` now contains an additional function, `bgr_array_to_yuv_buf` which can generate a YUV420 buffer in an equivalent format to that produced by the camera hardware. This allows image frames to be translated into YUV buffers. Frame data from the legacy pipeline may now be linked up with the LOW_POWERED pipeline.
- `camera.py` now has the facility to read camera frames from an emulated input, this integrates the `Vid2Frames.VideoStream` class into the legacy pipeline.
    - The `__init__` function now has an optional prameter, `read_from`. This can be used to pass an initialised `VideoStream`; when frames are read from the camera, they are in turn read from the `VideoStream` instance. s

### Changed
- Install script now downloads and installs the Vid2Frames library alongside DynAIkonTrap. If the vid2frames install fails, a warning message is given, the software is still usable without the library added. At present, the install is performed by downloading the vid2frames codebase from a tarball off Gitlab, the library is generated by building with cmake. This is thought to be adequate for production untill a more elegant packaging solution can be devised. 
- `EventProcessor` and `EventRememberer` logic is modified to read frames from disk without passing imformation about frame size and shape via thier pipeline predecessor. Frames are read from disk based on a file offset for each frame only. These offsets are computed in the `EventRememberer` and sorted and accessed in the `EventProcessor`

- `DirectoryMaker` is made far simpler with the removal of the `get_event` function and simplification of `new_event`:
  - Reliance on the `Path` library is removed, in favour of the simpler `os.path` tools. 
  - `new_event` function attempts to create a new event directory. If one cannot be made, then a temporary location is given in the `/tmp` directory.

- Raw YUV file format is modified to include the size of a given frame at the start of each frame buffer:
    - The file format now contains four bytes at the begginning of each frame representing two uint16 variables for the width and height of the frame. The size of the frame buffer can be easily calculated by reading these dimensions and doing some multiplication.
    - Within `video_buffers.py` the `write_inactive_stream` method within `RawRAMBuffer` is modified to write these parameters to file before the remainder of the video buffer is written. 
    - This change allows the size of each frame to be passed around with the file:
        - YUV data files are now more portable, reading does not rely on metadata passed around DynAIkonTrap
        - Metadata required for reading the files is cut down, less junk can be passed around in `EventData` class
        - Frames within a YUV data file can now be of changing sizes and still fully compatible with DynTrap
     


## [v1.3.1] - 2022-07-12
### Fixed
- DynTrap crashes using new pipeline in Send mode - fixed
    - WriterSettings object controled the `path` variable, this dictates where files are buffered on disk
    - `path` is now made a property of the base-class `OutputSettings`, `WriterSettings` is removed. 
    - We now have a base-class with required settings for send or disk modes, and an extension class, `SenderSettings` adds info for uploading detections to servers. 

### Added 
- New setttings fields are added to allow users to set
    - upload to fastcat-cloud or to use thier own server
    - add a userID and apiKey for fastcat-cloud uploads
    - specify the FCC endpoints (in case these change in future, or we have multiple mirrors)
- New sender modes in `comms.py`
    - allow video and image detections to be uploaded to FCC 
- Sender configuration testing in `comms.Output` function
    - tests if the server, userId, api keys are configured appropriately, if this fails, the user is notified via the log and a `Writer` instance is used instead
- Output methods in the `Sender` class now handle cases where the server is unavailable by saving to disk if the connection fails. 
- Ability to register the users FASTCAT-Cloud details in `tuner.py`
- Ability to post detections to FASTCAT-Cloud, made changes in `comms.py`, creates a log of 
- Feature to delete metadata files after conversion to output formats, switched on by default. May be turned off in `tuner.py`
- Ability to use FASTCAT-Cloud api to perform animal detection. 

### Changed 
- `Sender` now inherits from `Writer`
- H264 to mp4 format conversion moved to `imdecode.py`
- SenderSettings is created by default rather than OutputSettings. This allows FASTCAT-Cloud details to be simply passed to the animal filtering stages. Should be refactored in the future. 


## [v1.3.0] - 2022-06-04
### Fixed
- Increase `Serial` timeout to read full sensor line
- Memory overflow for reading large motion events from disk, new event processor only loads frames as and when required from IO

### Added - 2022-06-09
- ability to output log to a set file or standard out
- a much faster solution for SOTV of motion vectors. Can be seen in `motion.py` and `mvector_sum.pyx`, is written with Cython and tackles the biggest bottleneck of ndarray access time by accessing the memory directly using C. Around 50x faster than the original solution, produces the same results. 
- facility to read and save raw format YUV files
    - can now save YUV stream to `clip.dat` per event
    - decoding of all saved image frames now performed within `imdecode.py`
    - added YUV format to settings and tuner
    - YUV format uses less IO bandwidth, RPi zero w can now run at 20fps

### Changed - 2022-06-04
- removed many settings from `tuner.py` 
    - bitrate, removed from `tuner.py` and `settings.py` now set by default at 17000000, proven to work in testing on rpi0, rpi4
    - raw-framerate-divisor, removed from `tuner.py`, still configurable via `settings.py` now set to 1 (ie not required)
    - raw-pixel-format, removed from `tuner.py`, still configurable via `settings.py` now set to RGBA, stops PiCamera complaining
    - buffer size, removed from `tuner.py`, still configurable via `settings.py` now set to 20 secs, tested and works on rpi0, rpi4
- event processing now in its own file `DynAIkonTrap/filtering/event.py`
    - makes `filter.py` more concise
    - not built as a pipeline element (ie no input and output queues), perhaps to-do although seems superfluous...
- `EventData` class no longer carries frame buffers for an entire event
    - `remember_from_disk.py` no longer reads frame buffers, instead it scans the event file, making sure buffers exist and produces file pointers for the beginnning of each buffer, these are added to `EventData`
    - `EventData` also contains fields for frame width, height and pixel format, seems neater to pass them around as `EventData` than configure each pipeline element with those settings

## [v1.2.1] - 2021-11-24

### Added
- Support for TFLite trained SSDLite MobileNet v2 models
    - TFLite compiled binary wheel files for raspberry pi devices are included in `python_wheels/tflite_runtime`
        - at present installing through pip is experimental on RPi 4 and not possible on RPi Zero W, must be built from source.
    - `animal.py` modified to run inference using tflite networks or yolov4-tiny
    - `animal.py` `run_raw` and `run` modified to produce a `human_confidence` as well as `animal_confidence`
    - configuration for human detection, fast animal detection (tflite model) and thresholds for each added to settings.

### Fixed
    - fixed output queue length in `event_rememberer` to 1 not 10, this stops the system loading way too many motion events and exhausting memory (kswaps)
    - fixed indexing error in reading from motion buffer within `camera_to_disk.py`

### Changed
    - methods which use `animal.run` have been modified to accept human and animal values
    - changes in `setup.sh` insure tflite install is attempted

## [v1.2.0] - 2021-10-31
### Added
- Camera recording to disk module, modified PiCamera; DynCamera
- EventRememberer which to load events from disk into processing pipeline
- Filtermodes BY_FRAME and BY_EVENT to add functionality to process events with Filter module
- Event output added to comms.py
- modified __main__.py to support old and new pipelines depending on settings
- Modified settings to include parameters for: pipeline, bitrate, framerate divisor, buffer length, raw image format and detector fraction

### Changed
- Motion Queue Settings semantics changed to processing settings. To better fit other pipeline which does not use a motion queue.


## [v1.1.0] - 2021-08-15
### Added
- Check for `settings.json` version vs. DynAIkonTrap version in case settings are copied from one trap to another
- Added support for multiple output video codecs and settings to choose between them
- Pillow to requirements.txt easiest way to load raw images as far as I can tell. If this can be done with OpenCV it would be nicer.


### Fixed
- Implementation of UrSense interface following updated documentation
- Catches pycamera `ModuleNotFoundError` when running the camera trap with emulated input on desktop

### Changed
- Video sensor logs to JSON for easier machine reading -- parsing this back to the previous VTT output is trivial
- Interface to initialise `Output` -- output mode is now handled internally
- Documentation -- including wiki -- migrated to Sphinx


### Added
- context buffer so that clips of animals include "run in" and "trail off" frames.
- `LabelledFrames` now include a `motion_status` label of enumerated type `MotionStatus`
- `filtering.py` adds all frames to a `motion_sequence` regardless of motion score but labels frames passing through it.
- frames without motion are assigned a priority of -1.0 and a `MotionStatus` of `STILL` this ensures they are never returned by `get_highest_priority()` - thus never assessed for containing an animal.
- `MotionQueue` does not add motion sequences to its queue which do not contain motion. ie `end_motion_sequence()` now searches the sequence to make sure at least one frame is labelled with motion before appending to queue.


### Changed
- `MotionSequence` class is now called `Sequence`
- `MotionQueue` class is now called `MotionLabelledQueue`
---

## [v1.0.0] - 2021-06-12
### Added
- First release of DynAIkonTrap
