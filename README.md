# Pext

![Lilly the leoger](/logo.png)

[![ReadTheDocs](https://readthedocs.org/projects/pext/badge/?version=latest)](https://pext.readthedocs.io/en/latest/?badge=latest)
[![Translation status](https://hosted.weblate.org/widgets/pext/-/svg-badge.svg)](https://hosted.weblate.org/engage/pext/?utm_source=widget)
[![Code Health](https://landscape.io/github/Pext/Pext/master/landscape.svg?style=flat)](https://landscape.io/github/Pext/Pext/master)

## Contents

- [Community](#community)
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

## Community

If you need support or just want to chat with our community, we have the following options:

- IRC: #pext on OFTC ([webchat](https://webchat.oftc.net/?randomnick=1&channels=pext&prompt=1))
- Matrix: #pext:matrix.org ([webchat](https://riot.im/app/#/room/#pext:matrix.org))
- Telegram: [@PextTool](https://t.me/PextTool)

All these channels are linked to each other, so there is no need to worry about missing out.

We can also be reached on Twitter: [@PextTool](https://twitter.com/PextTool)

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

#### Arch

Pext is available as [pext](https://aur.archlinux.org/packages/pext/) and [pext-git](https://aur.archlinux.org/packages/pext-git/). These packages are maintained by [Ivan Semkin](https://github.com/vanyasem).

#### Other distros

We recommend the AppImages under GitHub releases, but you can also install from PyPI.

For the stable version (PyPI):

```sh
pip3 install pext --user
```

For the git version (PyPI):

```sh
pip3 install git+https://github.com/Pext/Pext.git --user
```

On some systems, you may need to use pip instead of pip3.

Alternatively, you can [install Pext from source](INSTALL_FROM_SOURCE.md)

### macOS

A macOS .dmg file is available [in the releases section on GitHub](https://github.com/Pext/Pext/releases). This is still experimental, please report any issues.

Alternatively, see [Installing Pext from source](INSTALL_FROM_SOURCE.md)

### Windows (experimental)

See [Installing Pext from source](INSTALL_FROM_SOURCE.md)

## Usage

To actually use Pext, you will first have to install one or more modules. Check out the Pext organisation on [GitHub](https://github.com/Pext) or use `Module` -> `Install module` -> `From online module list` in the application for a list of modules.

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

Pext user report: <https://github.com/Pext/Pext/issues/11>
Ubuntu bug: <https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826>

### macOS

#### I cannot brew/pip install anymore

The Homebrew team completely broke pip's --target flag, which Pext depends on. To work around this, Pext automatically creates a ``~/.pydistutils.cfg`` file which resets the broken Homebrew pip defaults and deletes this file after its done installing module dependencies.

As a side effect, this means that using brew install or pip install while Pext is installing module dependencies may fail. If you cannot use brew install or pip install at all anymore after Pext crashed, please delete ``~/.pydistutils.cfg`` if it exists.

The Homebrew team refuses to fix this issue: <https://github.com/Homebrew/brew/issues/837>

### Windows

#### The python or pip commands do not work/The PATH variable is wrong

In the installer, make sure that 'Include Python in PATH' or similar is checked. Then after the installation, start a new command prompt and type `python -V` or `pip3` to check if it was properly installed. If the version number and the help message are returned respectively, you are good to go further. If not, in case you already had `cmd.exe` open, restart it or execute `refreshenv` to reload environment variables.
If it still does not work yet, check if the PATH was set in the GUI or manually with `cmd.exe`.

GUI:

- Start Menu > Computer (right click) > Properties > Advanced System Settings > Environment Variables
- Check the PATH for both the system and the current user and in one of them the Python installation directory should be present, which is normally `C:\Python36` and `C:\Python36\Scripts`

cmd.exe:

- Run `path` or `echo %PATH%` to check if the directory (`C:\Python36` and `C:\Python36\Scripts`) is included
- The path can then be set with `setx` but because the possibility for truncation and the merging of users and system path, the gui method is to be preferred. (more details: <https://stackoverflow.com/questions/9546324/adding-directory-to-path-environment-variable-in-windows>)

## License

Pext is licensed under the [GNU GPLv3+](LICENSE), with exception of artwork and documentation, which are licensed under the [Creative Commons Attribution Share-Alike 4.0 license](LICENSE-CCBYSA).

Under artwork and documentation fall:

- All files in the following directories:
  - docs/
  - pext/images/
  - screenshots/
  - .github/
- All Markdown files in the root directory.
- logo.png

When attributing the logo (which was donated by [vaeringjar](https://notabug.org/vaeringjar)), it should be attributed as Lilly the leoger by White Paper Fox. Alternatively, it may be referred to as the Pext logo. Please link to Pext with <https://github.com/Pext/Pext> or <https://pext.hackerchick.me/> and to White Paper Fox with <http://www.whitepaperfox.com/> where possible.
