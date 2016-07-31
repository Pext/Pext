from abc import ABC, abstractmethod


class ModuleBase(ABC):
    """The base all Pext modules must implement."""
    @abstractmethod
    def init(self, binary, window, q):
        """Called when the module is first loaded.

        In this function, the application should initialize all its data and
        use the Action.addEntry and Action.addCommand to asynchronously
        populate the main list.

        If the list can be generated very quickly, the module may opt for using
        Action.replaceEntryList and Action.replaceCommandList instead, although
        it is recommended to queue the data per entry so that the user can
        start interacting with at least some of the data as quickly as
        possible.

        Each entry in the entry list must be a list containing the entry
        identifier and the searchable and displayed value. An example of a
        valid entry is ["supersecretpassword", "********"].

        Each entry in the command list must be a list containing the command
        identifier and the searchable and displayed value. An example of a
        valid entry is ["generate", "generate pass-name pass-length"].
        """
        pass

    @abstractmethod
    def stop(self):
        """Called when Pext is about to shut down, intended for cleaning up if
        required."""
        pass

    @abstractmethod
    def getAllEntryFields(self, entry):
        """Return a list of fields for a given entry.

        Each entry in the fields list must be a list containing the entry
        identifier and the searchable and displayed value. An example of a
        valid entry is ["supersecretpassword", "********"].

        If a list with zero values is returned, the identifier of the entry
        gets copied and the window is closed.

        If a list with a single value is returned, the identifier of that value
        gets copied and the window is closed.

        If a list with more than one value is returned, the displayed value of
        all those entries is shown on the screen, the identifier of the value
        that the user chooses gets copied to the clipboard and the window is
        closed.
        """
        pass

    @abstractmethod
    def runCommand(self, command, printOnSuccess=False, hideErrors=False):
        """Run a command."""
        pass

    @abstractmethod
    def processResponse(self, response):
        """Process a response given as a result of an Action being put into the
        queue. Not all Actions return a response.
        """
        pass
