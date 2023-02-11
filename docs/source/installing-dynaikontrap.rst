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

.. admonition:: Prerequisites
  :class: warning

  Unfortunately, DynAIkonTrap only works on Raspberry Pi systems at the moment.
  This is because of deep integrations with the ``picamera`` module.

Install on RPi
--------------

Prerequisites
^^^^^^^^^^^^^

Make sure your Raspberry Pi is up-to-date:

.. code:: sh

   sudo apt update && sudo apt upgrade -y

Then download and install the ``dynaikontrap-meta`` package which contains all
the required non-python system dependencies for DynAIkonTrap.

.. code:: sh

  wget https://dynaikon.com/resources/dynaikontrap-meta.deb -P /tmp/
  sudo apt install /tmp/dynaikontrap-meta.deb


Now you are ready to install DynAIkonTrap. Choose whether you would like to
install

* **From pre-packaged source**
  This is the easiest way to install DynAIkonTrap. This will install the latest
  release, packaged by us.

* **Manually from source**
  This will allow you to add your own changes to DynAIkonTrap, or to switch to
  an exact version.

From pre-packaged source
^^^^^^^^^^^^^^^^^^^^^^^^

This is easily done with one command

.. code:: sh

   pip3 install https://dynaikon.com/releases/DynAIkonTrap.tar.gz


Manually from source
^^^^^^^^^^^^^^^^^^^^

This option allows you to edit the source before installing. First ensure
``git`` is installed

.. code:: sh

  sudo apt install git

and then

.. code:: sh

  git clone https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap

This will download the source tree to ``dynaikontrap``. Enter the directory and
checkout to a commit of your choosing. Be aware that only tagged commits ``>
1.5.1`` will successfully build to a package. List tags with

.. code:: sh

   git tag --sort=taggerdate --list 'v[0-9]*'

You may also wish to make changes to the code. Once you are ready to install
your modified version of DynAIkonTrap, enter the root of the source tree and
execute

.. code:: sh

  python3 setup.py sdist
  pip3 install ./dist/DynAIkonTrap-x.y.z.tar.gz

Where ``x.y.z`` will be the version of the checked-out code.
