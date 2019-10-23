# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Changed
- Enable update check by default
- Use action to notify users about update checks being enabled

### Fixed
- Update action being added before translations are available

## [0.26] - 2019-10-18
### API changes
- Bump API version to 0.12.0
- Modules can now offer a multiple choice dialog using Action.ask_choice

### Added
- Explanation on Shift+Return key
- Support for metadata.json files to show a dropdown of choices
- Support for middle mouse button causing selection without minimization
- Buttons to open a new module or close the currently open module
- Support for reporting bugs to modules directly

### Changed
- Sorting settings are now per loaded module
- If there are no modules or themes, trying to load one will pop up the installation dialog
- macOS now also uses Qt's Fusion theme (less native, but less glitches)
- Update notifications are no longer in a dialog box
- Nightly versions now check for nightly updates

### Fixed
- TRANSLATION MISSING: failed_to_update_dependencies
- Global hotkey not working
- Back button remaining grey

## [0.25] - 2019-10-04
### API changes
- Bump API version to 0.11.1 so that modules can detect request handlers being fixed

### Added
- Shift+Return hotkey to explicitly disable minimizing and resetting when making a selection
- Ability to choose separator between output entries in queue (if more than one string will be output)

### Changed
- Text to copy to clipboard is now queued until minimizing too
- Default separator is now Enter instead of Tab
- If a selection state change is requested by the module, ensure it is always done

### Fixed
- Module request handlers not being removed properly, causing multiple incorrect requests

## [0.24.1] - 2019-09-08
### Changed
- Tab hotkeys changed from `Alt+<number>` to `Ctrl+<number>` on non-Linux for consistency with other applications

### Fixed
- Ctrl+Tab and Ctrl+Shift+Tab not working on macOS
- Module menu options which aren't usable in current context are now correctly grayed out

## [0.24.0] - 2019-06-28
### Packaging changes
- New macOS dependency: [PyAutoGUI](https://pypi.org/project/PyAutoGUI/)

### Added
- Turbo mode where Pext auto-selects options whenever reasonably confident

### Changed
- Notification when typing has completed

### Fixed
- Context menus are now searchable
- Don't crash if pynput fails to import
- User asked for internal update checker if disabled in constants
- Add repeat polyfill to prevent rendering issues on systems with older Qt versions
- Fix autotype on macOS

## [0.23] - 2019-03-19
### Packaging changes
- New dependency: [watchdog](https://pypi.org/project/watchdog/)

### API changes
- Bump API version to 0.10.0 so that modules can hide the header if it was used to show the tree
- Bump API version to 0.11.0 due to change in how a base context option is returned

### Added
- Searches can now be regular expressions. These need to be formatted as /search_string/flags
- Information when module requests are still being processed when showing no results screen
- Notification on copying data to clipboard

### Changed
- Modules are now automatically unloaded after uninstallation
- Passing arguments to modules is now done with Ctrl+Enter instead of typing it with the search bar
- The start screen now shows a hotkey reference
- The UI now shows what hotkey will activate what entry
- Right click / Ctrl+Return a context menu entry to activate command input mode if available
- The selection tree is now shown below the header location
- The "base" context menu is now merged with the entry-specific one and shown below the entry-specific options
- Command menu now has an "enter arguments" entry

### Fixed
- AppImage trying to store data inside itself in portable mode
- Some incorrect hotkeys on macOS
- Search sometimes missing entries

## [0.22] - 2018-12-19
### Added
- Portable builds for Linux and macOS
- --portable flag to make Pext behave more self-contained, readable by modules in settings

### Changed
- --config flag has been renamed to --data-path
- Remember the geometry of the main window
- The tray icon menu now lists all loaded modules for easier switching

### Fixed
- Sizing issues when moving to another monitor
- Window not being resizeable
- API version still being reported as 0.8.0 internally

## [0.21] - 2018-11-02
### API changes
- Bump API version to 0.9.0
- Commands can now be multiple words and arguments will be given in a new 'args' field
- ask_question_default_yes and ask_question_default_no are deprecated in favor of ask_question

### Changed
- Better error logging, using dialogs for critical errors
- Pext's Window is now 800x600 by default and centered on the screen

### Fixed
- Module installation issues on Windows and Linux Mint
- Title and tray tooltip are now translatable

## [0.20] - 2018-10-12
### Added
- Are you sure message when closing Pext normally
- Add installable touch bar quick action service for easier launching on macOS

### Changed
- Pick a more reasonable height on wide screens

### Fixed
- Minimize normally manually now works as intended
- Autotype now correctly queues up multiple entries to type
- Focus fix on macOS is now fast and reliable again
- Logo background is no longer misaligned

## [0.19] - 2018-09-05
### Added
- Foreground Pext at any time by pressing Ctrl+\`

### Changed
- Move upstream URLs to pext.io

### Fixed
- Fixed --module flag
- Fixed module install screens (from URL and from repo) failing when redirected

## [0.18] - 2018-08-22
### Added
- Belarusian translation (thanks, Nelly Simkova!)

### Fixed
- Module installation issues in Windows distribution

## [0.17] - 2018-07-08
### Packaging changes
- New dependency: [requests](https://pypi.org/project/requests/)

### Added
- Metadata i18n support
- No result text when filtering empties list

### Fixed
- Pext on macOS now ignores -psn_0_* arguments
- USE_INTERNAL_UPDATER is now used correctly
- Terminal window opening on Windows
- macOS certificate check failing on update check
- Off-by-one error in git describe version generation
- Installing module fails (rebuild on dulwich 0.9.15)

## [0.16] - 2018-06-22
### Packaging changes
- New dependency: [pynput](https://pypi.org/project/pynput/)
- New macOS dependency: [accessibility](https://pypi.org/project/accessibility)
- Dependency removal: notify-send

### Added
- Ability to switch output location on runtime
- Ability to type output directly
- Ability to automatically update modules
- Windows installer
- Polish translation

### Changed
- Switch to Qt5 for notifications
- Remove delay in showing notifications
- Core and module update checks are now done together
- Critical module errors now create a dialog box

### Fixed
- Inconsistent behaviour between clicking or selecting an entry
- MacOS menu not merging on non-English languages

## [0.15] - 2018-06-07
### Packaging changes
- The macOS .dmg is now officially supported

### Changed
- Remove quit without saving option
- Configuration changes are now saved instantly, instead of only on a clean quit

### Fixed
- Focus not resetting after Pext hiding on macOS
- Updated PyQt5 to fix some emoji display issues
- macOS .dmg not being able to install all modules

## [0.14] - 2018-04-22
### Packaging changes
- Packagers can now modify pext/constants.py to more easily control some behaviour

### Added
- French translation (thanks, Aurora Yeen!)

### Changed
- Modules are now installed by metadata.json, instead of by git URL
- Make pext_dev default to CC-BY-3.0 for themes

### Fixed
- Make text properly wrap in the installing from repository dialog
- Crashes on tab completion and minor errors (regression in 0.13)
- Crash on module reloading (regression in 0.13)
- IDs and names are now used more consistently
- Crash when trying to load a theme as a module
- Update pext_dev to be create files compatible with current Pext
- Pext profile locks are now per-user instead of globally (fixes being unable to start if another user is running Pext)

## [0.13] - 2018-04-07
### Added
- Hindi translation (thanks, Satyam Singh!)
- Add automatic AppImage builds (thanks, TheAssassin!)

### Changed
- Tray icon is now always shown when the application is minimized to tray
- Hide minimize to tray on macOS (too broken, can cause crashes)
- The main window now has a minimal size of 500x300
- Versioning now complies with PEP440
- Merge module and theme repo and object selection into a single screen to save a click
- Modules and themes are now saved based on the location of their ID
- Modules and themes being in an incorrect location for their ID are automatically removed

### Fixed
- Themes now apply properly on Windows (forcing Fusion styling)
- Properly fix i18n handling and giving i18n to modules
- The name setting in metadata.json is now consistently respected
- Make &Pext translatable

## [0.12] - 2018-03-04
### Added
- Support renaming profiles
- Switching profile from the GUI
- Opening a second instance with another profile from the GUI
- Basic profile management from the GUI
- Ability to change language through the UI
- `--list-locales` argument to show supported languages
- The installation screens now tell you if you already have a module or theme installed
- Russian translation (thanks, Ivan Semkin)

### Changed
- Profile name is no longer displayed if default
- Trying to create a profile that already exists throws an error
- Trying to delete a profile that is currently in use throws an error
- Use argparse for argument parsing instead of getopt
- Update checking now happens if the last check was over 24 hours, instead of each app launch
- Combine all menu groups in settings for organizational purposes
- Relicensed documentation under CC BY-SA 4.0

### Fixed
- Pext crash when module tries to empty context_menu_base
- Inconsistent font sizing
- Improved main screen resizing and logo showing
- Pext passing None as locale to modules in some cases
- --background stealing focus on macOS
- Modules and themes are now sorted correctly in the install from repository lists

### Removed
- Removed manpage

## [0.11.1] - 2017-12-19
### Packaging changes
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
