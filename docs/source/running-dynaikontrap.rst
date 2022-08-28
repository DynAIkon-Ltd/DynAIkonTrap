Running the Trap
================

Modes of Operation
------------------

We currently support two modes of operation

#. ``DynAikonTrap`` can operate on previously captured video files to detect
   animals.
#. ``DynAikonTrap`` can operate a camera module and work as an in-field Camera
   Trap.

Deployment in-field
-------------------

.. admonition:: Prerequisites
  :class: warning

  Prerequisites for this page are, that your Raspberry Pi

  #. Has Raspberry Pi OS **Buster**,

     Note that this is **not** the latest Raspberry Pi OS. Check
     ``/etc/os-release`` to see what ``VERSION_CODENAME`` you have. It must be
     ``buster``.
  #. Has the **camera module enabled, with a camera module that is working and
     in focus**,
  #. Has an **expanded filesystem**,
  #. you are **comfortable logging in** to your Raspberry Pi **remotely** over
     ``ssh``,
  #. and ``DynAIkonTrap`` **is installed**.

  If not, please refer to the sections :doc:`preparing-the-raspberry-pi` and
  :doc:`installing-dynaikontrap`.

#. Connect to your Raspberry Pi by using ``ssh`` from the terminal.
#. Start the camera trap code to make sure everything is working by typing the
   following on the terminal:

   .. code:: sh

      dynaikontrap

   After a few moments you should see the output from the camera trap software
   appearing. If you wave your hand in front of the camera you should begin to
   see messages about detected movement appearing.
#. To stop DynAikonTrap hit :kbd:`Ctrl+C`.

If you have reached this point, then well done! You have successfully set up the
camera trap.

The remaining sections on this page have some useful recommendations on how to
best use this camera trap, but if you are not very comfortable using a Raspberry
Pi yet you may want to stop here. Either way we do recommend that you have a
look at the :doc:`tuning-dynaikontrap` guide before deploying the camera trap
properly to make sure your system is fully optimised for your use-case.

Long-term deployment using ``screen``
-------------------------------------

If you start the code using the ``dynaikontrap`` command, the program will stop
as soon as you log out of the Raspberry Pi. This is not very useful as you will
likely not want to keep the terminal connection open for days or weeks on end. A
simple solution is to use the ``screen`` command.

Install ``screen`` with

.. code:: sh

   sudo apt install screen

then issue the following commands:

.. code:: sh

   # Start a new screen session called "dynaikontrap"
   screen -S dynaikontrap

   # Start the camera trap within the screen session
   dynaikontrap

You can now leave ``screen`` without stopping the camera trap code by hitting
:kbd:`Ctrl+A`, and then the :kbd:`D` key to "detach" from the session.

Now if you close the terminal/log out from the Raspberry Pi (:kbd:`Ctrl+D` or
``logout``), the camera trap will continue to run.


Checking progress
^^^^^^^^^^^^^^^^^

You can check progress easily using our DynAikonTrap web-viewer! This is a
server hosted on the deployed device. For more information on how to use the
web-viewer, check out our :doc:`Web-viewer page <web-viewer>`.

One can also use ``screen`` to monitor progress directly over ``ssh``. This is
easily done by starting an ``ssh`` session to the RPi. You can then reattach to
the ``screen`` session using:

.. code:: sh

   screen -r dynaikontrap

You will be able to see any logs produced by the DynAIkonTrap.


Stopping
^^^^^^^^

Reattach to the ``screen`` session as mentioned above for `Checking progress`_.
Once in the ``dynaikontrap`` session use :kbd:`Ctrl+C` to quit the DynAIkonTrap
code.

It is also safe to simply shutdown the Raspberry Pi by running:

.. code:: sh

   # "-h 0" means to "halt" in 0 seconds i.e. now
   sudo shutdown -h 0

The camera trap code will **not** automatically start again when the Raspberry
Pi is powered on. Remember to unplug the Raspberry Pi once it is shut down as it
will continue to use a very slight amount of energy if left plugged in.


Retrieving Observations from the Camera Trap
--------------------------------------------

The absolute simplest option for a novice Raspberry Pi user may be to plug the
SD card into their computer to access the files directly.

One can also retreive observations over the internet, using Secure Copy (SCP)
over SSH

.. code:: sh

   scp -a pi@dynaikontrap.local:~/dynaikontrap/output/ ./

copies all files from the default video output directory onto the current
directory on your computer.

Automatic
^^^^^^^^^
A slightly more complicated solution that allows automatic saving of files to a
separate device is as follows. If you have a second Raspberry Pi you could use
this as a server. Let's state some assumptions:

* The camera trap is called ``dynaikontrap``
* The output directory has been set to ``~/videos``
* The second computer (could be a second Raspberry Pi) is called ``server``

On ``dynaikontrap`` you could then run:

.. code:: sh

   sshfs ~/videos pi@server.local:~

to automatically save all files from ``dynaikontrap``'s output to the
``server``'s home directory. Note that ``sshfs`` may not be installed, but you
can install this with ``sudo apt install sshfs`` on Ubuntu/Debian systems. In
this configuration the files are actually saved physically to ``server``, so you
could have a more reliable hard disk drive on this device and serve the files to
other devices connected on the local network.

Server
^^^^^^

The camera trap does have a RESTful server API, but code for the server is not
released. This is left as an exercise for the reader. Using frameworks like
Django can make this a fairly simple process. We do not have the resources to
write and maintain the necessary code for this, but we would be happy to answer
questions you may have and hopefully help you set something up.

FASTCAT-Cloud

DynAIkonTrap integrates with DynAIkon's web API, FASTCAT-Cloud. This may be used
to upload detections automatically to your account through our API endpoints.
You can configure the camera trap to do this with your account details following
instructions on the :doc:`tuning` page.

Video Input
---------------

DynAIkonTrap may also be run on a static input as video processing software.
This allows pre-caught camera trap observation videos to be filtered using our
AI video pipeline.

To use this special mode, video files currently require some pre-processing
using a program called `ffmpeg`. This is installed on your system after running
`setup.sh`.

To pre-process a video file for parsing with DynAIkonTrap, use the command
shown:

   .. code:: sh

      ffmpeg -i input.mp4 -c:v mpeg4 -q:v 1 -an prepared-input.mp4

The resultant file, `prepared-input.mp4`, is suitable for processing with
DynAIkonTrap as shown:

   .. code:: sh

      dynaikontrap --filename prepared-input.mp4

This will run the camera trap on the video input, watch the output log to see if
animals are detected! When the video is processed, exit the program with
`CTRL+C`.
