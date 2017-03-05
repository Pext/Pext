![Pext logo](logo.png)

*Pext Logo by [White Paper Fox](http://whitepaperfox.com/) under
[Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
graciously donated by [Peers](https://peers.community/).*

# Introduction
Pext stands for **P**ython-based **ex**tendable **t**ool. It is build using
Python 3 and QML and intended to have its behaviour decided by modules. Pext
provides a simple window with a search bar, allowing modules to define what
data is shown and how it is manipulated.

Much like the leoger (a mix between a tiger and a leopard) in the logo, Pext
modules can turn Pext into a completely different beast. From password
management to weather information, modules can harness the full power of Python
to turn the deceitfully simple user interface into an useful and powerful
application.

![Pext](screencast.gif)  
*Pext running the [pass](https://github.com/Pext/pext_module_pass) and
[emoji](https://github.com/Pext/pext_module_emoji) modules*

# Dependencies
## Arch

    sudo pacman -S git python3 python-pip libnotify python-pyqt5 qt5-quickcontrols

## Debian (Stretch and later, no Jessie, sorry!)

    sudo apt-get install git libnotify-bin python3 python3-pyqt5 python3-pyqt5.qtquick qml-module-qtquick-controls

## Fedora

    sudo dnf install git libnotify python3 python3-qt5 qt5-qtquickcontrols

## macOS (Unsupported, but feel free to report bugs anyway)

    brew install python3 qt5 git libnotify
    pip3 install pyqt5 urllib3

# Installation (optional)
Pext does not need to be installed to run. However, if you prefer to install
it, you can do so:

    # pip3 install . --upgrade

# Usage
Simply start Pext with Python 3. If you have installed Pext using the above
command, simply start `pext`. Otherwise, go to the root directory and run
`pip3 install -r requirements.txt`
`python3 pext`.

To actually use Pext, you will first have to install one or more modules. Check
out the [Pext organisation on GitHub](https://github.com/Pext) for a list of
official modules.

For command line options, use `--help`.

# Hotkeys
## Entry management
- Escape: Go one level up
- Ctrl+J / Down arrow: Go one entry down
- Ctrl+H / Up arrow: Go one entry up
- Ctrl+F / Page down: Go one page down
- Ctrl+B / Page up: Go one page up
- Tab: Tab-complete the current input
- Enter: Select entry or run command

## Tab management
- Ctrl+T: Open new tab
- Ctrl+W: Close current tab
- Ctrl+Tab: Switch to next tab
- Ctrl+Shift+Tab: Switch to previous tab
- Alt+`<number>`: Switch to tab `<number>`
- F5: Reload tab, including code changes to the module

## Session management
- Ctrl+Q: Quit and save the currently loaded modules and settings to the profile
- Ctrl+Shift+Q: Quit without saving to the profile

# License
GPLv3+.
