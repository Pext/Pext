# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Packaging changes
- Pext now depends on pygit2, which uses libgit2, instead of git

### API changes
- Bump API version to 0.6.0
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

### Added
- Add info panels which modules can use to show extra info on the current status on selected entry
- Add context panels for state changes and extra actions for entries/commands
- Traceback is now printing when an exception is triggered
- Last updated info for modules
- Version info for modules
- Ability to update Pext itself if git is there

### Changed
- Command mode no longer locks onto the first entry
- Commands are always displayed in italics, instead of using italics for whatever is unfocused
- Versioning is now more precise
- Check if a module/theme has an update before updating it
- Pext now auto-restarts after changing the theme
- Pext now displays less broken when the height is higher than the width 

### Fixed
- Regression introduced in 0.9 which could cause selections to trigger wrongly when emptying the search bar
- Page up and down causing QML errors when used too close to the start/end of the list
- Minimizing behaviour didn't always work
- Git commands are now properly limited to Pext directories

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
