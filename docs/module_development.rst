Pext module development
=======================

Setting up the environment
--------------------------

Setting up the development environment is very easy. Simply installing Pext
as per the :doc:`README <README>` will also install pext_dev, containing all you need
to easily develop modules.

Once you have installed Pext, simply navigate to the directory you want to start
developing in and run ``pext_dev init`` to create a `__init__.py` file in the
current directory or ``pext_dev init <directory>`` to create a new directory
with a `__init__.py` file.

Starting module development
---------------------------

The generated `__init__.py` file is the main entry point to your Pext module
and the main and in many cases only file to edit. For editing, you can choose
any editor you like, so make sure to choose one that's comfortable for you to
work in.

If you open this file, you will see a few imports and a class named `Module`
which contains 4 functions. These are the core of any Pext module and you
need to fill these in with the Python 3 code you want to use. For more
information about the exact purpose of each of these functions, see
:doc:`pext_base`.

Sometimes you may want to use some Python libraries that don't come with
Python itself. In this case, you may place a file named `requirements.txt` in
your module's directory, listing one Python module you want per line. Python
modules can be found on `PyPI <https://pypi.python.org/pypi>`_. Make sure you
check the license of modules you want to use for compatibility with your
module's license (``pext_dev init`` defaults to GPLv3+).

More advanced information on using a `requirements.txt` file can be found on
`<https://pip.readthedocs.io/en/latest/reference/pip_install/#requirements-file-format>`_.

Testing
-------

To test your module, simply run ``pext_dev run`` in the module directory. This
will launch a completely clean instance of Pext and install your module from
scratch, including dependencies defined in `requirements.txt`. This way you can
be reasonably sure your module will work for others too. When you're done
testing, simply close the Pext instance that popped up and pext_dev will clean
everything up again.

Publishing your module
----------------------

To publish your module, put it on a git hosting site such as
`NotABug <https://notabug.org/>`_. Make sure to add a README file so users who
find your module online know what it's about!

Whenever you make a change to your module, you can push it to git and, as long
as it's on the master branch, Pext will update to the new version as soon as
the user asks for module updates. Simple as that.

If you want your module to be listed in Pext under `Other Developers`, please
`get in touch <https://pext.hackerchick.me/#community>`_.

