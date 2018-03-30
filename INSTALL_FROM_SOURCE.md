# Installing Pext from source
All of these steps assume you have already downloaded Pext and are currently in the root directory of the download.

## GNU/Linux
### Preparation
The following dependencies need to be installed:

#### Arch

    sudo pacman -S libnotify python-pip python-pyqt5 qt5-quickcontrols

You will also need python-dulwich from the AUR.

#### Debian

    sudo apt-get install libnotify-bin python3-pip python3-dulwich python3-pyqt5.qtquick qml-module-qtquick-controls

You may also need to install libssl1.0-dev due to what seems like a Debian packaging issue. See https://stackoverflow.com/a/42297296 for more info.

#### Fedora

    sudo dnf install libnotify python3-dulwich python3-pip python3-qt5 qt5-qtquickcontrols

#### Nix (any system, not just NixOS)

    nix-shell -p libnotify python3Packages.pip python3Packages.dulwich python3Packages.pyqt5 qt5.qtquickcontrols

#### openSUSE

    sudo zypper install libnotify-tools python3-dulwich python3-pip python3-qt5

### Starting Pext
After installing the dependencies, Pext can be ran by running one of the following commands in the place where you saved Pext to:
- ``python3 pext`` to start Pext itself
- ``python3 pext_dev`` to start the Pext tools for module and theme development

If desired, it can also be installed using the following command:

    $ pip3 install . --user --upgrade --no-deps

After doing this, you can start Pext like any application, or use ``pext`` and ``pext_dev`` on the command line.

## macOS
### Preparation
The following commands need to be run. If you do not have the brew command, follow the installation instructions on [Homebrew's website](https://brew.sh/).

Before running the Install Certificates command, which is only necessary to be able to retrieve the online module list, please read https://bugs.python.org/msg283984.

    brew install libnotify python3 qt5
    pip3 install certifi dulwich pyqt5 urllib3
    /Applications/Python\ 3.6/Install\ Certificates.command

### Starting Pext
After installing the dependencies, Pext can be ran by running one of the following commands in a terminal window in the place where you saved Pext to:
- ``python3 pext`` to start Pext itself
- ``python3 pext_dev`` to start the Pext tools for module and theme development

If desired, it can also be installed using the following command:

    $ pip3 install . --user --upgrade --no-deps

After doing this (and adding "$HOME/Library/Python/3.6/bin" to your $PATH), you can start Pext like any application, or use ``pext`` and ``pext_dev`` on the command line.

Optionally, a .app file can be generated using the following commands:

    ./build_mac_app.sh

The .app file appears in the dist directory and can be dragged to "My Applications".

## Windows (experimental)
### Preparation
Assuming you have no previous python installation, either 

- Use a package manager like [Chocolatey](http://chocolatey.org/) to install Python 3
- Install Python 3.6 manually from https://www.python.org/downloads/windows/

Then, assuming python and pip are installed, run `pip install dulwich PyQt5` in a command window.

### Starting Pext
Pext can be ran by ran from a command window by running one of the following commands in the place where you saved Pext to (type ``cd place_you_saved_pext`` to go there):
- ``python pext`` to start Pext itself
- ``python pext_dev`` to start the Pext tools for module and theme development

