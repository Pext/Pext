# Pext

![Pext logo](/logo.png)

*Pext Logo by [White Paper Fox](http://whitepaperfox.com/) under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
graciously donated by [vaeringjar](https://notabug.org/vaeringjar).*

[![ReadTheDocs](https://readthedocs.org/projects/pext/badge/?version=latest)](https://pext.readthedocs.io/en/latest/?badge=latest)
[![Translation status](https://hosted.weblate.org/widgets/pext/-/svg-badge.svg)](https://hosted.weblate.org/engage/pext/?utm_source=widget)

## Contents
- [Introduction](#introduction)
- [How it works](#how-it-works)
- [Installation](#installation)
  - [GNU/Linux](#gnulinux)
  - [macOS](#macos)
  - [Windows (experimental)](#windows-experimental)
- [Usage](#usage)
- [Hotkeys](#hotkeys)
- [Troubleshooting](#troubleshooting)
  - [GNU/Linux](#gnulinux-1)
  - [macOS](#macos-1)
  - [Windows](#windows)
- [License](#license)

## Introduction
Pext stands for **P**ython-based **ex**tendable **t**ool. It is built using Python 3 and Qt5 QML and has its behaviour decided by modules. Pext provides a simple window with a search bar, allowing modules to define what data is shown and how it is manipulated.

For example, say you want to use Pext as a password manager. You load in the pass module, and it will show you a list of your passwords which you can filter with the search bar. When you select a password in the list, it will copy the password to your clipboard and Pext will hide itself, waiting for you to ask for it again.

Depending on the module you choose, what entries are shown and what happens when you select an entry changes. So choose the module appropriate for what you want to do, and Pext makes it easy.

Several modules are available for effortless install right within Pext.

![Pext running the radiobrowser module with info panel](/screenshots/pext_radiobrowser_infopanel.png)  
![Pext running the openweathermap module with context menu](/screenshots/pext_openweathermap_contextmenu.png)  
![Pext running the emoji module](/screenshots/pext_emoji.png)

## How it works
Pext is designed to quickly pop up and get out of your way as soon as you're done with something. It is recommended to bind Pext to some global hotkey, or possibly run multiple instances of it with different profiles under multiple hotkeys. Example Pext workflows look as follows:

![Pext workflow graph](/workflow_graph.png)

Simply put:
- Open (Pext)
- Search (for something)
- Select (with Enter)
- Hide (automatically)

## Installation
**Note: If you run into any issues, please check out the troubleshooting section near the end of this document before reporting a bug.**

### GNU/Linux
#### Preparation
The following dependencies need to be installed:

##### Arch

    sudo pacman -S libnotify python-pip python-pygit2 python-pyqt5 qt5-quickcontrols

##### Debian

    sudo apt-get install libnotify-bin python3-pip python3-pygit2 python3-pyqt5.qtquick qml-module-qtquick-controls

You may also need to install libssl1.0-dev due to what seems like a Debian packaging issue. See https://stackoverflow.com/a/42297296 for more info.

##### Fedora

    sudo dnf install libnotify python3-pip python3-pygit2 python3-qt5 qt5-qtquickcontrols

##### Nix (any system, not just NixOS)

    nix-shell -p libnotify python3Packages.pip python3Packages.pygit2 python3Packages.pyqt5 qt5.qtquickcontrols

##### openSUSE

    sudo zypper install libnotify-tools python-pygit2 python3-pip python3-qt5

#### Starting Pext
After installing the dependencies, Pext can be ran by running one of the following commands in the place where you saved Pext to:
- ``python3 pext`` to start Pext itself
- ``python3 pext_dev`` to start the Pext tools for module and theme development

If desired, it can also be installed using the following command (as root):

    # pip3 install . --upgrade --no-deps

After doing this, you can start Pext like any application, or use ``pext`` and ``pext_dev`` on the command line.

### macOS
#### Preparation
The following commands need to be run. If you do not have the brew command, follow the installation instructions on [Homebrew's website](https://brew.sh/).

Before running the Install Certificates command, which is only necessary to be able to retrieve the online module list, please read https://bugs.python.org/msg283984.

    brew install libgit2 libnotify python3 qt5
    pip3 install certifi pygit2 pyqt5 urllib3
    /Applications/Python\ 3.6/Install\ Certificates.command

#### Starting Pext
After installing the dependencies, Pext can be ran by running one of the following commands in a terminal window in the place where you saved Pext to:
- ``python3 pext`` to start Pext itself
- ``python3 pext_dev`` to start the Pext tools for module and theme development

Optionally, a .app file can be generated using the following command:

    python3 setup.py py2app -A --emulate-shell-environment

The .app file appears in the dist directory and can be dragged to "My Applications". Please note that actual py2app buils do not work yet. This is an aliased build, so it will break if you delete your git clone.

### Windows (experimental)
#### Preparation
Assuming you have no previous python installation, either 

- Use a package manager like [Chocolatey](http://chocolatey.org/) to install Python 3
- Install Python 3.6 manually from https://www.python.org/downloads/windows/

Then, assuming python and pip are installed, run `pip install PyQt5 pygit2` in a command window.

#### Starting Pext
Pext can be ran by ran from a command window by running one of the following commands in the place where you saved Pext to (type ``cd place_you_saved_pext`` to go there):
- ``python pext`` to start Pext itself
- ``python pext_dev`` to start the Pext tools for module and theme development

## Usage
To actually use Pext, you will first have to install one or more modules. Check out the Pext organisation on [GitHub](https://github.com/Pext) or [NotABug](https://notabug.org/Pext) or use `Module` -> `Install module` -> `From online module list` in the application for a list of modules.

After installating at least one module, you can load it from the `Module` -> `Load module` menu. After that, experiment! Each module is different.

For command line options, use `--help`.

## Hotkeys
### Entry management
- Escape: Go one level up
- Tab: Tab-complete the current input
- Enter / Left mouse button: Select entry or run command
- Ctrl+Shift+. / Right mouse button on header: Open state menu
- Ctrl+. / Right mouse button on any item: Open context menu
- Ctrl+J / Down arrow: Go one entry down
- Ctrl+H / Up arrow: Go one entry up
- Ctrl+F / Page down: Go one page down
- Ctrl+B / Page up: Go one page up

### Tab management
- Ctrl+T: Open new tab
- Ctrl+W: Close current tab
- Ctrl+Tab: Switch to next tab
- Ctrl+Shift+Tab: Switch to previous tab
- Alt+`<number>`: Switch to tab `<number>`
- F5: Reload tab, including code changes to the module

### Session management
- Ctrl+Q: Quit and save the currently loaded modules and settings to the profile
- Ctrl+Shift+Q: Quit without saving to the profile

## Troubleshooting
### GNU/Linux
#### Installing module dependencies fails
Your distribution may ship with an outdated version of pip. Run ``pip install --upgrade pip`` (possibly as root) in a terminal.

#### Pext's window is completely white
The proprietary NVIDIA driver is known to cause this issue on at least Ubuntu. You can work around this by running ``sudo apt-get install python3-opengl``.

Pext user report: https://github.com/Pext/Pext/issues/11  
Ubuntu bug: https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826

### macOS
#### I cannot brew/pip install anymore
The Homebrew team completely broke pip's --target flag, which Pext depends on. To work around this, Pext automatically creates a ``~/.pydistutils.cfg`` file which resets the broken Homebrew pip defaults and deletes this file after its done installing module dependencies.

As a side effect, this means that using brew install or pip install while Pext is installing module dependencies may fail. If you cannot use brew install or pip install at all anymore after Pext crashed, please delete ``~/.pydistutils.cfg`` if it exists.

The Homebrew team refuses to fix this issue: https://github.com/Homebrew/brew/issues/837

### Windows
#### The python or pip commands do not work/The PATH variable is wrong

In the installer, make sure that 'Include Python in PATH' or similar is checked. Then after the installation, start a new command prompt and type `python -V` or `pip3` to check if it was properly installed. If the version number and the help message are returned respectively, you are good to go further. If not, in case you already had `cmd.exe` open, restart it or execute `refreshenv` to reload environment variables.
If it still does not work yet, check if the PATH was set in the GUI or manually with `cmd.exe`.

GUI:

- Start Menu > Computer (right click) > Properties > Advanced System Settings > Environment Variables
- Check the PATH for both the system and the current user and in one of them the Python installation directory should be present, which is normally `C:\Python36` and `C:\Python36\Scripts`

cmd.exe:

- Run `path` or `echo %PATH%` to check if the directory (`C:\Python36` and `C:\Python36\Scripts`) is included
- The path can then be set with `setx` but because the possibility for truncation and the merging of users and system path, the gui method is to be preferred. (more details: https://stackoverflow.com/questions/9546324/adding-directory-to-path-environment-variable-in-windows)

## License
GPLv3+.
