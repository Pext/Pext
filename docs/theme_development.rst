Pext theme development
=======================

Setting up the environment
--------------------------

Setting up the development environment is very easy. Simply installing Pext
as per the :doc:`README <README>` will also install pext_dev, containing all you need
to easily develop themes.

Once you have installed Pext, simply navigate to the directory you want to start
developing in and run ``pext_dev theme init`` to create the base files in the current
directory or ``pext_dev theme init <directory>`` to create them in a new directory.

Starting module development
---------------------------

After running ``pext_dev theme init`` and answering its questions you will have a
directory with the following files in it:

- theme.conf
- metadata.json
- LICENSE

The generated `theme.conf` file is your theme. For editing, you can choose
any editor you like, so make sure to choose one that's comfortable for you to
work in.

If you open this file, you will see a single line with the text "[All]". This
is called a Color Group. A Color Group tells the theming engine when to apply
the theming. Valid values are as follows:

- Disabled: when the window can't be interacted with
- Active (or Normal): the "normal" state
- Inactive: when the window is in the background
- All: A fallback for if no specific Color Rule is defined in another Group

Each Color Group consists of one or more Color Roles. A Color Role tells the
theming engine what UI element to apply the color to. Color Roles are written
as simple key = value lines with the value containing 3 numbers for the amount
of red, green and blue (RGB) ranging from 0 to 255.

For example, to make the window pure red when the window is inactive, you would
write this in `theme.conf`:

.. code-block:: none

   [Inactive]
   Window = 255,0,0

For a complete list of all Color Roles, please see
`the QPalette docs <https://doc.qt.io/qt-5/qpalette.html#ColorRole-enum>`_.
Please remember to only use the names after `::`. So, instead of using
`QPalette::Window` as key, simply use `Window`.

One thing to note is that the theming engine automatically processes colors, so
you may not exactly get the color you are looking for, but a close
approximation instead.

The `metadata.json` file contains general information on your module, used by
Pext to show the user who developed the module, its intended purpose and more,
both when the user is about to install the module and when they already
installed it.

`LICENSE` contains the license for your project. ``pext_dev theme init`` puts the
Creative Commons Attribution 3.0 license into this file, as it is a common Open
Source license for non-code files.

Testing
-------

To test your theme, simply run ``pext_dev theme run`` in the theme directory. This
will launch a completely clean instance of Pext running your theme. When you're done
testing, simply close the Pext instance that popped up and pext_dev will clean
everything up again.

Publishing your theme
----------------------

To publish your theme, put it on a git hosting site such as
`GitHub <https://github.com/>`_. Make sure to add a README file so users who
find your theme online know what it's about!

Whenever you make a change to your theme, you can push it to git and, as long
as it's on the master branch, Pext will update to the new version as soon as
the user asks for theme updates. Simple as that.

If you want your theme to be listed in Pext under `Other Developers`, please
`get in touch <https://pext.hackerchick.me/#community>`_.

