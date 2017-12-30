# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Added
- Support renaming profiles
- Switching profile from the GUI
- Opening a second instance with another profile from the GUI
- Basic profile management from the GUI

### Changed
- Profile name is no longer displayed if default
- Trying to create a profile that already exists throws an error
- Trying to delete a profile that is currently in use throws an error
- Use argparse for argument parsing instead of getopt
- Update checking now happens if the last check was over 24 hours, instead of each app launch

### Fixed
- Pext crash when module tries to empty context_menu_base

### Removed
- Removed manpage

## [0.11.1] - 2017-12-19
### Packaging
- Fix missing translation files

## [0.11] - 2017-12-19
### Packaging changes
- Pext now depends on dulwich
- Pext no longer depends on pygit2

### Translation updates
- Added Norwegian Bokmål (thanks, Allan Nordhøy!)
- Update Chinese (Traditional) translation
- Update Spanish translation
- Update Hungarian translation
- Update Dutch translation

### Fixed
- Ubuntu/Debian compatibility for git operations over HTTPS
- Install module from URL screen not working (regression from adding theming support for 0.9)
- Theme selector now correctly displays current theme before switching
- Pext no longer creates an empty theme file for the system theme and doesn't show it in the list of themes

## [0.10] - 2017-11-11
### Packaging changes
- Pext now depends on pygit2, which uses libgit2, instead of git

### API changes
- Bump API version to 0.7.0
- Add set_entry_info queue call
- Add replace_entry_info_dict queue call
- Add set_command_info queue call
- Add replace_command_info_dict queue call
- Add set_base_info queue call
- Add set_entry_context queue call
- Add replace_entry_context_dict queue call
- Add set_command_context queue call
- Add replace_command_context_dict queue call
- Add set_base_context queue call
- Add extra_info_request function
- Add a none SelectionType
- Made more parameters optional

### Added
- Add info panels which modules can use to show extra info on the current status on selected entry
- Add context panels for state changes and extra actions for entries/commands
- Traceback is now printing when an exception is triggered
- Last updated info for modules
- Version info for modules
- Windows support
- Support for checking for updates (stable versions only)

### Changed
- Command mode no longer locks onto the first entry
- Commands are always displayed in italics, instead of using italics for whatever is unfocused
- Versioning is now more precise
- Check if a module/theme has an update before updating it
- Pext now auto-restarts after changing the theme
- Pext now displays less broken when the height is higher than the width
- Removed tray menu because it can't be translated due to PyQt limitations
- Make clicking the tray icon toggle visibility on macOS
- Minimizing normally after Pext is done is now the default on all platforms
- Module requesting window hide will only reset the selection of that module instead of all
- The --exit option got removed, Pext now will only start the UI if no options were given or all options were session-related

### Fixed
- Regression introduced in 0.9 which could cause selections to trigger wrongly when emptying the search bar
- Page up and down causing QML errors when used too close to the start/end of the list
- Minimizing behaviour didn't always work
- Git commands are now properly limited to Pext directories
- Desktop notifications now also show when Pext is minimized normally
- Modules no longer lock up Pext while making a selection
- Direct Git URL clone ending in / no longer creates an undeletable module
- Modules now always properly get localization info
- Ugly line between entries and entry info in some themes
- No themes available dialog now correctly shows
- Modules can't crash Pext by throwing an exception on stopping on Pext exit

## [0.9] - 2017-08-23
### API changes
- Whenever the state changes (either by the user going back, selecting something or set_selection being called), the queue is now emptied
- ask_input and ask_input_password now ask for a prefill before the identifier

### Translation updates
- Added traditional Chinese (thanks, Jeff Huang!)
- Added Spanish (thanks, Emily Lau!)
- Updated Dutch (thanks, Heimen Stoffels!)

### Added
- Theming support based on QPalette
- UI option to choose minimizing behaviour
- UI option to choose sorting behaviour
- UI toggle to enable/disable tray icon
- --background command line option to make Pext not launch/foreground the UI

### Changed
- The design philosophy is now explained in the empty state screen
- pyqt5 is added as install_requires
- The about dialog now thanks translators
- Info-only CLI parameters will no longer launch Pext as well (--help, --version, --list-styles, --list-modules, --list-themes)
- Closing the main window will now quit Pext and save state

### Fixed
- pext_dev's generated base file now leaves the copyright open for the author to fill in
- Not being able to select an entry until the list is fully loaded
- Selection constantly resetting while items are being added
- Loading and reloading a module while text is in search now applies the filter correctly
- Fix crash in command mode when pressing enter while hovering over a wrong entry

## [0.8] - 2017-04-28
### API changes
- The settings variable now contains _api_version ([major, minor, patch]) and _locale by default
- Queue requests that cause process_response to be called can now optionally give an identifier to receive when process_response is called
- Modules must now declare their settings in metadata.json

### Added
- Simple pext_dev command to help module development
- Support metadata.json for showing info on installed modules
- i18n support
- Dutch translation

### Changed
- Move all UI code to QML
- Improved installation dialogs
- Improve load module dialog
- Get rid of update and uninstall dialogs in favor for a central module management dialog
- Check module functions parameter length on module load to prevent some runtime crashes for modules
- Module settings is no longer a freeform input field
- Display "Waiting" instead of "Ready" in the statusbar when not processing and the active module has not sent anything yet

### Fixed
- Crash when picking a command while there are also other entries to display

### Removed
- config.ini for editing Pext config directory (use $XDG_CONFIG_HOME or $HOME instead)

## [0.7] - 2017-04-10
### Added
- Clear/back button in the UI

### Changed
- Minor UI font size changes
- Pext's QML now uses StandardKeys in most places

### Fixed
- Fix Debian detection (no longer incorrectly detects openSUSE as Debian)
- Fix nonsense load/update/uninstall dialogs if no modules are installed

## [0.6.1] - 2017-04-01
### Fixed
- Clicking the tray icon no longer toggles visibility on macOS
- XDG_CONFIG_HOME is now correctly used when available
- The environment is no longer cleared when doing the initial git clone (security: the old behaviour would cause a proxy defined in the environment to be ignored)

## [0.6] - 2017-03-27
### Added
- Install dependencies automatically if the module provides a requirements.txt file

### Fixed
- If module installation fails, the module directory is removed, so a subsequent installation doesn't instantly fail
- Modules are now correctly unloaded when they raise a critical error
- Added workaround for Ubuntu systems running the proprietary nvidia driver (https://github.com/Pext/Pext/issues/11)

## [0.5] - 2017-03-22
### API changes
- Remove Action.notify_message and Action.notify_error, which are synonyms for add_message and add_error

### Added
- Documentation
- Repository for third-party modules

### Changed
- Give more information upon installing modules and warn the user that they are code
- User commands will now be auto-completed to the selected command

### Fixed
- Files unexpectedly existing in ~/.config/pext/modules/ no longer causes a crash

## [0.4.1] - 2017-03-05
### Changed
- The default window is no longer explicitly borderless
- The logo now has a white background which improves readability on dark themes

### Fixed
- An error occuring when retrieving the list of downloadable modules no longer causes a crash
- Selecting a command entry after the entry list no longer causes a crash

## [0.4] - 2017-02-20
### Added
- Basic Qt5 theming support using installed system themes
- Allow for a pext/config.ini file to overwrite some default configuration
- Allow the user to disable tray icon creation
- Add entry to open homepage from help menu (so the user can find support)

### Changed
- Get list of installable modules from pext.hackerchick.me instead of pext.github.io

## [0.3] - 2016-12-29
### API changes
- The entry and command list will now be emptied each time just before selection_made is called

### Added
- Busy indicator when the list of entries is empty for a more responsive look
- Support for getting a list of installable modules from pext.github.io

### Fixed
- All commands now correctly show up after emptying the search bar
- Module lists are now sorted alphabetically
- selection_made is no longer unnecessarily triggered when closing the window

## [0.2] - 2016-11-21
### Added
- System tray icon

## [0.1] - 2016-11-19
Initial release
