Building Documentation
======================

This page documents how to build the documentation. You can use these steps to
check everything displays correctly locally before pushing changes.

There are currently two options to build documentation: using a docker container
or manually. We recommend using the Docker method to guarantee that the
documentation builds correctly.

Using docker container (Recommended)
------------------------------------

Using the ``docs/docker-build-documentation.sh`` script, build the documentation
in a containerised environment. It will watch the given source directory and
re-build the documentation on every file change. The usage is

.. code-block:: sh

  bash docs/docker-build-documentation.sh <DynAikonTrap git repository>

This command will produce a ``html`` tree of the documentation under
``<DynAikonTrap git repository>/docs/build/html``. To read the documentation
navigate your web browser (Firefox/Chrome) to ``<DynAikonTrap git
repository>/docs/build/html/index.html``. Exit the container with :kbd:`Ctrl+C`.

For example, when the current directory is the root of the DynAikonTrap git
repository, one can call

.. code-block:: sh

  bash docs/docker-build-documentation.sh .

to produce the documentation under ``DynAikonTrap/docs/build/html``.

If executed from within ``DynAikonTrap/docs``, one would have to alter the
command to

.. code-block:: sh

  bash docker-build-documentaiton.sh ..

This is the recommended method, since this project is very sensitive to which
``python`` version and ``pip`` package versions are installed. Indeed,
``Sphinx`` (the toolkit used for automatically generating the code
documentation) needs to be able to import the ``DynAIkonTrap`` module (and all
its dependencies). It can only do this if all the correct versions are
installed. Else conflicts are possible. We have also experienced documentation
build failures with specific versions of ``numpy``.

Using the ``python:3.7`` container allows us to have a tightly controlled
environment in which we know the documentation will build correctly.


Manually
--------

This assumes you are in the ``DynAikonTrap/docs`` directory.

First initialise a virtual environment

.. code-block:: sh

  pip install virtualenv
  virtualenv venv
  source venv/bin/activate
  pip install --upgrade pip

Install the requirements from the DynAIkonTrap module and those required for
building the documentation.

.. code-block:: sh

  # To allow building on non-RaspberryPi platforms
  export READTHEDOCS=True
  # Install the DynAIkonTrap dependencies
  pip install -r ../requirements.txt
  # Install the dependencies required for building the documentation
  pip install -r requirements.txt

Now build the documentation

.. code-block:: sh

  make clean
  make html

To read the documentation navigate your web browser (Firefox/Chrome) to
``DynAikonTrap/docs/build/html/index.html``.
