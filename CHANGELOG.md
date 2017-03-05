# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
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
