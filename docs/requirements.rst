Requirements
============

Modules may specify Python requirements in a ``requirements.txt`` file.

The requirements should be specified one requirement per line, with the version number explicitly specified to prevent unexpected breakage due to upstream changes.

More advanced information on using a `requirements.txt` file can be found on `<https://pip.readthedocs.io/en/latest/reference/pip_install/#requirements-file-format>`_.

For more up-to-date examples, look at any of the modules or themes in the `Pext GitHub organisation <https://github.com/Pext>`__.

Example
-------

::

    dulwich==0.19.13
    paramiko==2.6.0
    pypass==0.2.1
    Babel==2.7.0
    git+https://github.com/TheLastProject/pyotp@5d7bf9d10e3bdef8c93917c1f4f5ffcf799a671e#egg=pyotp
    pyscreenshot==0.5.1
    zbar-py==1.0.4
