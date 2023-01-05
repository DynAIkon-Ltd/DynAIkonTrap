Tuning the Trap
===============

Now that everything is installed, the system needs to be tuned for your
use-case. You can investigate tuning options and configure outputs using our
``dynaikontrap-config`` program.

To run ``dynaikontrap-config`` simply type:

.. code:: sh

   dynaikontrap-config

This will bring up a graphical window which you can navigate via the terminal,
use the arrow keys and keyboard to change the settings for DynAIkonTrap.

Using ``dynaikontrap-config``, you can check out all the parameters for the
system to use. These settings are saved in a ``settings.json`` file, which is
loaded when you start the actual camera trap program. Below is relevant
information for settings parameters:

.. admonition:: Pipeline
   :class: note

   This dictates the processing pipeline DynAikonTrap will use, information
   about each pipeline may be found in :doc:`pipelines`, for a low-powered
   HD resolution video camera trap, choose the LOW_POWER option.

.. admonition:: Framerate
   :class: note

   Number of frames that are captured by the camera every second. Testing
   indicates this should not exceed 20 FPS for HD resolutions. If you require a
   higher frame-rate than this, it is recomended to use the legacy pipeline and
   drop the resolution down considerably, ie to 640x480 (VGA).

.. admonition:: Resolution
   :class: note

   Dimensions of the captured images and video. This is specified using width
   and height in the tuning script. Take a look at the relevant `PiCamera
   documentation
   <https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes>`_ for
   information on valid width and height combinations for your camera model.
   Also check that the chosen resolution supports video mode at the desired
   framerate. Note that certain dimensions limit the field of view of the
   camera.

.. admonition:: Visible animal area to trigger
   :class: note

   The expected visible area (on a plane parallel to the camera lens) of a
   subject animal, expressed in square-metres. This is used to determine what
   amount of motion will trigger the camera.

.. admonition:: Expected distance of animal from sensor
   :class: note

   Roughly the distance you would expect your subject animal to be from the
   camera sensor. A sensible value here may be around a metre, although you are
   encouraged to try out different values.

.. admonition:: Animal trigger speed
   :class: note

   The minimum speed, in metres per second, you would require your animal to
   travel at for motion to be triggered. Ensure this is not too low, so the
   animal detection stage is not overwhelmed with motion sequences. If you would
   like to set a low threshold make sure the background is not likely to
   experience movement, for example by pointing the camera at a wall rather than
   a bush.

.. admonition:: Camera focal length
   :class: note

   Focal length, in **metres**, as stated by the manufacturer. You may find
   `this summary table
   <https://www.raspberrypi.org/documentation/hardware/camera/>`_ helpful.

.. admonition:: Pixel size
   :class: note

   Pixel size, in **metres**, (single dimension) as stated by the manufacturer.
   You may find `this summary table
   <https://www.raspberrypi.org/documentation/hardware/camera/>`_ helpful.

.. admonition:: Number of pixels
   :class: note

   Sensor resolution width as stated by the manufacturer. You may find `this
   summary table <https://www.raspberrypi.org/documentation/hardware/camera/>`_
   helpful.

.. admonition:: SoTV small movement threshold
   :class: note

   The initial threshold applied to all movement vectors independently. This
   should be a small value and is given in pixel dimensions.

.. admonition:: SoTV smoothing IIR order
   :class: note

   Order for the IIR filter on the output of the SoTV motion filtering stage.
   Testing has shown that an order of 3 is appropriate to minimise delays whilst
   still achieving the desired smoothing effect.

.. admonition:: SoTV smoothing IIR stop-band attenuation
   :class: note

   Amount by which the frequencies in the stop-band are to be attenuated by, in
   dB. These are the higher frequencies that are to be removed, leading to a
   smoother output. -35dB has been found to work well here.

.. admonition:: Animal confidence threshold
   :class: note

   Confidence value to be exceeded for the animal detector to declare a frame as
   containing an animal.

.. admonition:: FASTCAT-Cloud animal detect
   :class: note

   This option configures the camera trap to query our FASTCAT-Cloud API for
   deep neural network animal detection rather than running model inference on
   device. Our models available online are much larger and more accurate at
   detecting species and can be used so long as the device has a valid internet
   connection during deployment.

.. admonition:: Filter humans
   :class: note

   As well as filtering for animal detections, we also have a model available
   on-device which can distinguish humans from animals. If this option is
   selected, DynAIkonTrap will attempt to throw away any video/image detections
   which it deems as containing a human to protect individual privacy in
   deployed locations.

.. admonition:: Human confidence threshold
   :class: note

   Confidence value to be exceeded for the human detector to declare a frame as
   containing an human.

.. admonition:: Maximum motion sequence period
   :class: note

   Maximum length for a single motion sequence, in seconds. A new motion
   sequence is started if the current one exceed this limit.

.. admonition:: Motion context buffer length
   :class: note

   This is a low-powered pipeline parameter. The number of seconds selects the
   amount of video for head and tail context to detections. For example, a
   produced video may have a number of recorded seconds before animal enters
   frame and some seconds of video after it has left. We call this context time.

.. admonition:: Fraction of event to process with neural network.
   :class: note

   This is a low-powered pipeline parameter. This is the fraction of raw frames
   which are processed with a neural network in the worst case in our spiral
   inference scheme. Higher fractions will result in more required computation
   as a trade off for higher recall of animal events. It is reccomended to set
   this value to 0.0 for low-compute capable devices, such as Raspberry Pi Zero
   W and to 1.0 for more capable devices, such as Raspberry Pi 4B

.. admonition:: Sensor board port
   :class: note

   Port to be used to communicate with the USB sensor board. This will usually
   be ``/dev/ttyUSB0``.

.. admonition:: Sensor board baud rate
   :class: note

   Baud rate to be used to communicate with the USB sensor board.

.. admonition:: Sensor reading interval
   :class: note

   Interval, in seconds, at which the sensor board is read.

.. admonition:: Output mode
   :class: note

   Choose between saving to disk (``d``) or sending data to a server (``s``) via
   HTTP requests. If picking the latter you will need to configure a server to
   use the simple API.

.. admonition:: FASTCAT-Cloud upload
   :class: note

   This option configures DynAIkonTrap to upload its observations to your
   FASTCAT-Cloud account. If no internet connection can be established,
   detections will be written to disk instead.

.. admonition:: Output path
   :class: note

   A location for all recordings to be saved to. Leaving this empty saves them
   in the DynAIkonTrap project directory, by default, it's set to a folder
   called `output`.

.. admonition:: Server address
   :class: note

   URI of the server to which captures are to be transmitted using the
   implemented API.

.. admonition:: Output format
   :class: note

   Whether or not output is to be saved in video format. The alternative is to
   output still images.

.. admonition:: Device ID
   :class: note

   An identifier to use for the camera trap. This is not used other than in
   output meta-data. This could be used to uniquely identify camera traps if
   multiple of these are in use.

.. admonition:: Delete metadata
   :class: note

   In the low-powered pipeline, DynAIkonTrap buffers video to disk which is
   analysed with a background process. It may be desirable to keep these
   metadata for further processing/debugging. This option allows the user to
   disable deleting metadata.

.. admonition:: Logging level
   :class: note

   Choose the minimum threshold for logging. Messages with a level below this
   will not be output. The recommended level is ``INFO`` as this provides
   informative, but not excessive, output.

.. admonition:: Logger output file
   :class: note

   This dictates the file DynAikonTrap will output log messages to. By default,
   this is set to `/dev/stdout`, which will cause log messages to appear at the
   terminal. If you wish to save a system log, add a file name of your choice.


You may also configure these settings via our legacy ``tuner.py`` script,
although it is a bit less user friendly!

.. code:: sh

   dynaikontrap-tuner
