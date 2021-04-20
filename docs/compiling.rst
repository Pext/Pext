Compiling from source
=====================

Please note that these instructions are for developers. If you want to just use Pext, look into `installation <installation.html>`__.

Windows
-------

Preparation
```````````

Assuming you have no previous python installation, either

- Use a package manager like `Chocolatey <http://chocolatey.org/>`__ to install Python 3
- Install Python 3.6 manually from `python.org <https://www.python.org/downloads/windows/>`__

Then, assuming python and pip are installed, run `pip install dulwich PyQt5 pynput` in a command window.

Starting Pext
`````````````

Pext can be ran by ran from a command window by running one of the following commands in the place where you saved Pext to (type ``cd place_you_saved_pext`` to go there):

- ``python -m pext`` to start Pext itself
- ``python -m pext_dev`` to start the Pext tools for module and theme developmentAlternatively, see See [Installing Pext from source](INSTALL_FROM_SOURCE.md) (not recommended and unsupported)

macOS
-----

Preparation
```````````

The following commands need to be run. If you do not have the brew command, follow the installation instructions on `Homebrew's website <https://brew.sh/>`__.

Before running the Install Certificates command, which is only necessary to be able to retrieve the online module list, please read https://bugs.python.org/msg283984.

::

  brew install libnotify python3 qt5
  pip3 install certifi dulwich pyqt5 urllib3
  /Applications/Python\ 3.6/Install\ Certificates.command

Starting Pext
`````````````

After installing the dependencies, Pext can be ran by running one of the following commands in a terminal window in the place where you saved Pext to:

- ``python3 -m pext`` to start Pext itself
- ``python3 -m pext_dev`` to start the Pext tools for module and theme development

If desired, it can also be installed using the following command::

  pip3 install . --user --upgrade --no-deps

After doing this (and adding "$HOME/Library/Python/3.6/bin" to your $PATH), you can start Pext like any application, or use ``pext`` and ``pext_dev`` on the command line.

GNU/Linux
---------

The following dependencies need to be installed:

============ ========
Distribution Packages
============ ========
Arch Linux   libnotify python-pip python-pyqt5 qt5-quickcontrols python-dulwich (AUR)
NixOS        libnotify python3Packages.pip python3Packages.dulwich python3Packages.pyqt5 qt5.qtquickcontrols
openSUSE     libnotify-tools python3-dulwich python3-pip python3-qt5
============ ========

After installing the dependencies, Pext can be ran by running one of the following commands in the place where you saved Pext to:

- ``python3 -m pext`` to start Pext itself
- ``python3 -m pext_dev`` to start the Pext tools for module and theme development

If desired, it can also be installed using the following command (pip instead of pip3 on some systems)::

  pip3 install . --user --upgrade --no-deps

After doing this, you can start Pext like any application, or use ``pext`` and ``pext_dev`` on the command line.

