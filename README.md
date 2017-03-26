# Pext

![Pext logo](/logo.png)

*Pext Logo by [White Paper Fox](http://whitepaperfox.com/) under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
graciously donated by [Peers](https://peers.community/).*

[![ReadTheDocs latest](https://readthedocs.org/projects/pext/badge/?version=latest)](https://pext.readthedocs.io/en/latest/?badge=latest)
[![ReadTheDocs stable](https://readthedocs.org/projects/pext/badge/?version=stable)](https://pext.readthedocs.io/en/stable/?badge=stable)

## Introduction
Pext stands for **P**ython-based **ex**tendable **t**ool. It is built using
Python 3 and Qt5 QML and intended to have its behaviour decided by modules. Pext
provides a simple window with a search bar, allowing modules to define what
data is shown and how it is manipulated.

Much like the leoger (a mix between a tiger and a leopard) in the logo, Pext
modules can turn Pext into a completely different beast. From password
management to weather information, modules can harness the full power of Python
to turn the simple user interface into an useful and powerful application.

![Pext](/screencast.gif)  
*Pext running the [pass](https://github.com/Pext/pext_module_pass) and
[emoji](https://github.com/Pext/pext_module_emoji) modules*

## Dependencies
### Arch

    sudo pacman -S git python-pip libnotify python-pyqt5 qt5-quickcontrols

### Debian (Stretch and later, no Jessie, sorry!)

    sudo apt-get install git libnotify-bin python3-pip python3-pyqt5.qtquick qml-module-qtquick-controls

### Fedora

    sudo dnf install git libnotify python3-pip python3-qt5 qt5-qtquickcontrols

### macOS
Before running the Install Certificates command, which is only necessary to be
able to retrieve the online module list, please read https://bugs.python.org/msg283984.

    brew install python3 qt5 git libnotify
    pip3 install pyqt5 urllib3 certifi
    /Applications/Python\ 3.6/Install\ Certificates.command

## Installation (optional)
Pext does not need to be installed to run. However, if you prefer to install
it, you can do so:

    # pip3 install . --upgrade

## Usage
Simply start Pext with Python 3. If you have installed Pext using the above
command, simply start `pext`. Otherwise, go to the project's root directory and
run `python3 pext`.

To actually use Pext, you will first have to install one or more modules. Check
out the Pext organisation on
[GitHub](https://github.com/Pext) or [NotABug](https://notabug.org/Pext)
or use `Module` -> `Install module` -> `From online module list` in the
application for a list of official modules.

For command line options, use `--help`.

## Troubleshooting
### GNU/Linux
#### Installing module dependencies fails
Your distribution may ship with an outdated version of pip. Run
``pip install --upgrade pip`` (possibly as root) in a terminal.

#### Pext's window is completely white
The proprietary NVIDIA driver is known to cause this issue on at least Ubuntu.
You can work around this by running ``sudo apt-get install python3-opengl``.

Pext user report: https://github.com/Pext/Pext/issues/11
Ubuntu bug: https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826

### macOS
#### I cannot brew/pip install anymore
The Homebrew team completely broke pip's --target flag, which Pext depends on.
To work around this, Pext automatically creates a ``~/.pydistutils.cfg`` file
which resets the broken Homebrew pip defaults and deletes this file after its
done installing module dependencies.

As a side effect, this means that using brew install or pip install while Pext
is installing module dependencies may fail. If you cannot use brew install or
pip install at all anymore after Pext crashed, please delete
``~/.pydistutils.cfg`` if it exists.

The Homebrew team refuses to fix this issue: https://github.com/Homebrew/brew/issues/837

## Hotkeys
### Entry management
- Escape: Go one level up
- Ctrl+J / Down arrow: Go one entry down
- Ctrl+H / Up arrow: Go one entry up
- Ctrl+F / Page down: Go one page down
- Ctrl+B / Page up: Go one page up
- Tab: Tab-complete the current input
- Enter: Select entry or run command

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

## License
GPLv3+.
