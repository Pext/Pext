API
===

Base
----
Every module needs to have a module class which inherits from ModuleBase.

Example:

.. literalinclude:: pext_dev/module/__init__.py

See `pext_base.py <pext_base.html>`_ for detailed information about every function.

Helpers
-------
Pext provides 2 helpers for modules.

Action
~~~~~~
The first type is the Action helper, which supply a list of actions which modules can request Pext to do.

See `pext_helpers.py <pext_helpers.html#pext_helpers.Action>`_ for a list of Actions.

SelectionType
~~~~~~~~~~~~~
The second type is the SelectionType helper, which supplies an enumerator containing possible selection types that Pext may pass to some functions.

See `pext_helpers.py <pext_helpers.html#pext_helpers.SelectionType>`_ for a list of SelectionTypes.
