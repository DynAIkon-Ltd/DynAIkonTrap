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
Provides access to a preset Python logger. To use call :func:`get_logger` once at the start of the file with the parameter set to ``__name__``. Doing so ensures the logging output displays which module a log message was generated in.

Example usage:

.. code:: py

   logger = get_logger(__name__)
   
   logger.error('A dreadful thing is happening')
"""
from logging import Logger, basicConfig, getLogger
from os import getenv
from stat import filemode


def set_logger_config(output_file="/dev/stdout", level="DEBUG"):
    """Sets up the logger configuration, can pass a file path describing where the logger prints to. Default is /dev/stdout.

    Args:
        output_file (str, optional): Output file path where the logger prints to. Defaults to '/dev/stdout'.
    """
    logging_level = level
    mode = (
        "w" if output_file == "/dev/stdout" else "a"
    )  # cannot write in append mode to /dev/stdout
    basicConfig(
        filename=output_file,
        filemode=mode,
        level=logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_logger(name: str) -> Logger:
    """Creates a :class:`logging.Logger` instance with messages set to print the path according to ``name``. The function should always be called with ``__name__``

    Args:
        name (str): file path as given by ``__name__``

    Returns:
        Logger: A :class:`Logger` instance. Call the standard info, warning, error, etc. functions to generate
    """
    return getLogger(name)
