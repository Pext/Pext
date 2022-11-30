Installation
============

Please note that these instructions are for normal installation. If you instead want to help develop, look into `compiling from source <compiling.html>`__.

Windows
-------
A Windows installer is available `in the releases section on GitHub <https://github.com/Pext/Pext/releases>`__.

macOS
-----
A macOS .dmg file is available `in the releases section on GitHub <https://github.com/Pext/Pext/releases>`__.

Alternatively, you may install Pext through pip::

  pip install pext

If you are unable to run Pext due to Gatekeeper settings, run the following command to allow running programs from any source::

  sudo spctl --master-disable

You may also need to go to Security & Privacy settings and select "Allow apps downloaded from: Anywhere"

GNU/Linux
---------

Arch Linux
``````````
Pext is available as `pext <https://aur.archlinux.org/packages/pext/>`__ and `pext-git <https://aur.archlinux.org/packages/pext-git/>`__. These packages are maintained by `Agesly Danzig <https://github.com/agesly>`__.

Other distros
`````````````
An AppImage is available `in the releases section on GitHub <https://github.com/Pext/Pext/releases>`__. It can be ran in-place on pretty much any GNU/Linux distribution. Make sure to right click the AppImage and mark it as executable in properties. Then, just double click.

Alternatively, you may install Pext through pip::

  pip3 install --user pext

On some systems, you may need to use pip instead of pip3.
