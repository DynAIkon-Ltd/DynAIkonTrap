.. toctree::
  :hidden:

  preparing-the-raspberry-pi.rst
  installing-dynaikontrap.rst
  running-dynaikontrap.rst
  web-viewer.rst
  tuning.rst
  deploying-dynaikontrap.rst

  pipelines/
  dev-docs/
  about.rst

  revisions.rst
  changelog.rst
  Project GitLab <https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap>

DynAIkonTrap: Camera Trapping on the Raspberry Pi
-------------------------------------------------

*An AI-enabled camera trap design targeted at the* **Raspberry Pi platform**.

DynAIkonTrap makes use of a continuous stream from a camera attached to the
Raspberry Pi, analysing only the stream to detect animals. Animal detections can
be used to save or send individual frames from the video, or even whole video
segments. The beauty of this is that the system does not rely on any secondary
sensors like PIR sensors and acts on exactly what the camera sees.

This project is part of the COS4Cloud research project funded by the EU.

What is a Camera Trap?
______________________

A Camera Trap is a camera that is automatically triggered by changes in its
surrounding environment, for example an animal moving past the camera.


What is FASTCAT?
________________

FASTCAT is DynAIkon's specification for Flexible Ai SysTem for CAmera Traps. It
comprises of a Cloud component and an Edge component. The specification for
FASTCAT-Cloud describes a service that is centrally hosted to which a network of
camera traps can connect, and upload their observations to get high precision
species detections.

The FASTCAT-Edge specification describes an individual camera that performs
animal detection in real time at the edge. This can be standalone or a part of a
network that pools all observations.

.. image:: _static/fastcat-edge.png
  :target: _static/fastcat-edge.pdf
  :width: 800
  :alt: Description of FASTCAT-Edge

The corresponding FASTCAT-Cloud service on the web is described
`here  <https://cos4cloud-eosc.eu/services/fastcat-cloud-camera-trap>`_.


DynAIkonTrap as an instance of FASTCAT-Edge
___________________________________________

Whilst FASTCAT-Edge is a specification, DynAIkonTrap is an instance of the
specification. It combines all the necessary hardware and software to perform
observations at the Edge.
