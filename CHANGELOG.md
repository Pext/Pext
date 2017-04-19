# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### API changes
- The settings variable now contains _api_version ([major, minor, patch]) and _locale by default
- Queue requests that cause process_response to be called can now optionally give an identifier to receive when process_response is called

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
