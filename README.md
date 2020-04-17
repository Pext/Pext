# Pext

<a href="https://repology.org/metapackage/pext/versions">
    <img src="https://repology.org/badge/vertical-allrepos/pext.svg?minversion=0.30" alt="Packaging status" align="right">
</a>

![Lilly the leoger](/assets/logo.png)

[![REUSE status](https://api.reuse.software/badge/github.com/Pext/Pext)](https://api.reuse.software/info/github.com/Pext/Pext)
[![Linux & macOS Build Status](https://travis-ci.org/Pext/Pext.svg?branch=master)](https://travis-ci.org/Pext/Pext)
[![Windows Build status](https://ci.appveyor.com/api/projects/status/73oaa4x1spa5vumx/branch/master?svg=true)](https://ci.appveyor.com/project/TheLastProject/pext/branch/master)
[![ReadTheDocs](https://readthedocs.org/projects/pext/badge/?version=latest)](https://pext.readthedocs.io/en/latest/?badge=latest)
[![Translation status](https://hosted.weblate.org/widgets/pext/-/svg-badge.svg)](https://hosted.weblate.org/engage/pext/?utm_source=widget)

[![Matrix](https://img.shields.io/matrix/pext:matrix.org.svg)](https://riot.im/app/#/room/#pext:matrix.org)

## Contents

- [Introduction](#introduction)
- [How it works](#how-it-works)
- [Installation](https://pext.readthedocs.io/en/latest/installation.html)
- [Usage](#usage)
- [Hotkeys](#hotkeys)
- [Community](#community)
- [License](#license)


## Introduction

Pext stands for **P**ython-based **ex**tendable **t**ool. It is built using Python 3 and Qt5 QML and has its behaviour decided by modules. Pext provides a simple window with a search bar, allowing modules to define what data is shown and how it is manipulated.

For example, say you want to use Pext as a password manager. You load in the pass module, and it will show you a list of your passwords which you can filter with the search bar. When you select a password in the list, it will copy the password to your clipboard and Pext will hide itself, waiting for you to ask for it again.

Depending on the module you choose, what entries are shown and what happens when you select an entry changes. So choose the module appropriate for what you want to do, and Pext makes it easy.

Several modules are available for effortless install right within Pext.

![Pext Introduction](/assets/pext_intro.gif)

## How it works

Pext is designed to quickly pop up and get out of your way as soon as you're done with something. It is recommended to bind Pext to some global hotkey, or possibly run multiple instances of it with different profiles under multiple hotkeys. Example Pext workflows look as follows:

![Pext workflow graph](/assets/workflow_graph.png)

Simply put:

- Open (Pext)
- Search (for something)
- Select (with Enter)
- Hide (automatically)

## Usage

To actually use Pext, you will first have to install one or more modules. Check out the Pext organisation on [GitHub](https://github.com/Pext) or use `Module` -> `Install module` -> `From online module list` in the application for a list of modules.

After installating at least one module, you can load it from the `Module` -> `Load module` menu. After that, experiment! Each module is different.

For command line options, use `--help`.

## Hotkeys

### Entry management

- Escape: Go one level up
- Shift+Escape: Go up to top level and trigger minimize
- Tab: Tab-complete the current input
- Enter / Left mouse button: Select entry or run command
- Shift+Enter: Select entry or run command but explicitly disable minimizing
- Ctrl+Enter: Run command with arguments
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

- Ctrl+Q: Quit

## Community

If you need support or just want to chat with our community, we have the following options:

- Matrix: #pext:matrix.org ([webchat](https://riot.im/app/#/room/#pext:matrix.org))
- Telegram: [@PextTool](https://t.me/PextTool)
- IRC: #pext on FreeNode ([webchat](http://webchat.freenode.net/?channels=%23pext&uio=MTY9dHJ1ZQ79))

All these channels are linked to each other, so there is no need to worry about missing out.

We can also be reached on Twitter: [@PextTool](https://twitter.com/PextTool)

## License

Pext is licensed under the [GNU GPLv3+](LICENSES/GPL-3.0-or-later.txt), with exception of artwork and documentation, which are licensed under the [Creative Commons Attribution Share-Alike 4.0 license](LICENSES/CC-BY-SA-4.0.txt).

Under artwork and documentation fall:

- All files in the following directories:
  - assets/
  - docs/
  - pext/images/
  - .github/
- All Markdown files in the root directory.

When attributing the logo (which was donated by [vaeringjar](https://notabug.org/vaeringjar)), it should be attributed as Lilly the leoger by White Paper Fox. Alternatively, it may be referred to as the Pext logo. Please link to Pext with <https://github.com/Pext/Pext> or <https://pext.io/> and to White Paper Fox with <http://www.whitepaperfox.com/> where possible.
