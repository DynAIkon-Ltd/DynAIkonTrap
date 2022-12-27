Installing DynAikonTrap
=======================

.. admonition:: Prerequisites
  :class: warning

  Prerequisites for this page are, that your Raspberry Pi

  #. Has Raspberry Pi OS **Buster**,

     Note that this is **not** the latest Raspberry Pi OS. Check
     ``/etc/os-release`` to see what ``VERSION_CODENAME`` you have. It must be
     ``buster``.
  #. Has the **camera module enabled, with a camera module that is working and
     in focus**,
  #. Has an **expanded filesystem**, and
  #. You are **comfortable logging in** to your Raspberry Pi **remotely** over
     ``ssh``,

  If not, please refer to the sections :doc:`preparing-the-raspberry-pi`.

Install on RPi
--------------

Make sure your Raspberry Pi is up-to-date:

.. code:: sh

   sudo apt update && sudo apt upgrade -y

Make sure ``git`` is installed by running:

.. code:: sh

   sudo apt install -y git

Then download the code with

.. code:: sh

   git clone https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap.git

and naviagte to the latest stable version of DynAIkonTrap with

.. code:: sh

   (cd dynaikontrap && git checkout -q $(git tag --sort=taggerdate --list 'v[0-9]*' | tail -1))

Finally, run the setup script with:

.. code:: sh

   bash dynaikontrap/setup.sh

This may take a little time to complete, but once it is done you should be able
to start the camera trap code by running ``dynaikontrap``.

Raspberry Pi settings
^^^^^^^^^^^^^^^^^^^^^

There are a few settings that need to be configured using ``sudo raspi-config``.
These include enabling the camera and enabling Wi-Fi as required. You may also
wish to change your hostname to ``dynaikontrap`` for compatibility with the
remaining instructions, although it isn't essential.


Installation on Other Platforms (not Raspberry Pi)
--------------------------------------------------

.. important::

   You cannot run the full DynAIkonTrap on a non-RPi system out of the box. You
   can, however, use our `vid2frames
   <https://gitlab.dynaikon.com/dynaikontrap/vid2frames>`_ library or run the
   `evaluation script
   <https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap#evaluation>`_.

If you are installing on another platform like your desktop or laptop you will
need to run:

.. code:: sh

   export READTHEDOCS=True

before

.. code:: sh

   ./setup.sh

This instructs the installer to not install the full version of the PiCamera
library as that only runs on the Raspberry Pi.
