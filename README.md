# Pext

![Pext logo](/logo.png)

*Pext Logo by [White Paper Fox](http://whitepaperfox.com/) under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
graciously donated by [vaeringjar](https://notabug.org/vaeringjar).*

[![ReadTheDocs latest](https://readthedocs.org/projects/pext/badge/?version=latest)](https://pext.readthedocs.io/en/latest/?badge=latest)
[![ReadTheDocs stable](https://readthedocs.org/projects/pext/badge/?version=stable)](https://pext.readthedocs.io/en/stable/?badge=stable)
[![Translation status](https://hosted.weblate.org/widgets/pext/-/svg-badge.svg)](https://hosted.weblate.org/engage/pext/?utm_source=widget)

## Introduction
Pext stands for **P**ython-based **ex**tendable **t**ool. It is built using
Python 3 and Qt5 QML and has its behaviour decided by modules. Pext provides
a simple window with a search bar, allowing modules to define what data is
shown and how it is manipulated.

For example, say you want to use Pext as a password manager. You load in the
pass module, and it will show you a list of your passwords which you can
filter with the search bar. When you select a password in the list, it will
copy the password to your clipboard and Pext will hide itself, waiting for you
to ask for it again.

Depending on the module you choose, what entries are shown and what happens
when you select an entry changes. So choose the module appropriate for what you
want to do, and Pext makes it easy.

Several modules are available for effortless install right within Pext.

![Pext running the radiobrowser module with info panel](/pext_radiobrowser_infopanel.png)  
![Pext running the openweathermap module with context menu](/pext_openweathermap_contextmenu.png)  
![Pext running the emoji module](/pext_emoji.png)

## How it works
Pext is designed to quickly pop up and get out of your way as soon as you're done with something. It is recommended to bind Pext to some global hotkey, or possibly run multiple instances of it with different profiles under multiple hotkeys. Example Pext workflows look as follows:

![Pext workflow graph](/workflow_graph.png)

Simply put:
- Open (Pext)
- Search (for something)
- Select (with Enter)
- Hide (automatically)

## Dependencies
### GNU/Linux
#### Arch

    sudo pacman -S libnotify python-pip python-pygit2 python-pyqt5 qt5-quickcontrols

#### Debian (Stable (9) and later)

    sudo apt-get install libnotify-bin python3-pip python3-pygit2 python3-pyqt5.qtquick qml-module-qtquick-controls

You may also need to install libssl1.0-dev due to what seems like a Debian packaging issue. See https://stackoverflow.com/a/42297296 for more info.

#### Fedora

    sudo dnf install libnotify python3-pip python3-pygit2 python3-qt5 qt5-qtquickcontrols

#### Nix (any system, not just NixOS)

    nix-shell -p libnotify python3Packages.pip python3Packages.pygit2 python3Packages.pyqt5 qt5.qtquickcontrols

#### openSUSE

    sudo zypper install libnotify-tools python-pygit2 python3-pip python3-qt5

### macOS
Before running the Install Certificates command, which is only necessary to be
able to retrieve the online module list, please read https://bugs.python.org/msg283984.

    brew install libgit2 libnotify python3 qt5
    pip3 install certifi pygit2 pyqt5 urllib3
    /Applications/Python\ 3.6/Install\ Certificates.command

After this, a .app file can be generated using the following command:

    python3 setup.py py2app -A --emulate-shell-environment

The .app file appears in the dist directory and can be dragged to
"My Applications". Please note that actual py2app buils do not work yet. This
is an aliased build, so it will break if you delete your git clone.

## Installation (optional)
Pext does not need to be installed to run. However, if you prefer to install
it, you can do so:

    # pip3 install . --upgrade --no-deps

This also installs pext_dev, to aid module development.

## Usage
Simply start Pext with Python 3. If you have installed Pext using the above
command, simply start `pext`. Otherwise, go to the project's root directory and
run `python3 pext`.

To actually use Pext, you will first have to install one or more modules. Check
out the Pext organisation on
[GitHub](https://github.com/Pext) or [NotABug](https://notabug.org/Pext)
or use `Module` -> `Install module` -> `From online module list` in the
application for a list of modules.

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

## License
GPLv3+.
