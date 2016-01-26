## PyPass
PyPass is a Python-based password and todo-list manager, built using QML,
heavily inspired by [GoPass](https://github.com/cortex/gopass).

![Screencast](screencast.gif)
*The above screencast is updated manually and may not be up-to-date with the
latest development. Also, the background image is the default KDE Plasma 5.4
wallpaper and not part of PyPass.*

When started without parameters, it defaults to being a password manager using
the excellent [pass](http://www.passwordstore.org/) password store. However, it
can also be called with --store=todo.sh to be used as a todo-list manager using
the [official todo.txt cli app](https://github.com/ginatrapani/todo.txt-cli).

## Usage
Just start typing. When the entry you want to use is displayed at the top, hit
enter to copy it to your clipboard. Many useful commands can also be executed
straight from PyPass. Entries can be tab-completed, even when typing a command.

Of course, you can also select another entry in the list, either with the
arrow keys or with vim-style Ctrl+K and Ctrl+J bindings. The selected entry is
highlighted in red. If mice are your thing, your trustworthy rodent can select
an entry with a single click.

To get the most out of PyPass, set up your system to start it with a global
hotkey, so you can always quickly access a password (or your todo list) when
you need it.

## License
GPLv3+.
