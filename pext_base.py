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

        The entry list must be a list containing all possible values as
        strings.
        """
        pass

    @abstractmethod
    def stop(self):
        """Called when Pext is about to shut down, intended for cleaning up if
        required."""
        pass

    @abstractmethod
    def selectionMade(self, selection):
        """Called when the user makes a selection.

        The selection variable contains a list of the selection tree.

        For example, if the user chooses "Settings" in the main screen, the
        value of selection is ["Settings"]. If the user then chooses "Audio",
        this function is called again, with the value of selection being
        ["Settings", "Audio"].
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
