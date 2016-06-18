## Pext
Pext stands for **P**ython-based **ex**tendable **t**ool. It is build using
Python 3 and QML and intended to have its behaviour decided by modules. Its user
interface is heavily inspired by [GoPass](https://github.com/cortex/gopass).

![Screencast](screencast.gif)  
*The above screencast shows Pext being used as a password manager. It is
is not necessarily a good indication up-to-date with the latest development
version.  
The background image is the default KDE Plasma 5.4 wallpaper and not
part of Pext.*

## Usage
Just start typing. When the entry you want to use is displayed at the top, hit
enter to interact with it or, if no further interaction is supported, copy it
to your clipboard. Entries can be tab-completed, even when typing a command.

Of course, you can also select another entry in the list, either with the
arrow keys or with vim-style Ctrl+K and Ctrl+J bindings. The selected entry is
highlighted in red. If mice are your thing, your trustworthy rodent can select
an entry with a single click.

To get the most out of Pext, set up your system to start it with a global
hotkey, so you can always quickly access a password (or your todo list) when
you need it.

## Dependencies
### Debian

    sudo apt-get install python3 python3-pyqt5 python3-pyqt5.qtquick qml-module-qtquick-controls python3-pexpect python3-pyinotify pass

## License
GPLv3+.
