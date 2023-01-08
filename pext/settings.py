#!/usr/bin/env python3

# Copyright (c) 2015 - 2023 Sylvia van Os <sylvia@hackerchick.me>
#
# This file is part of Pext.
#
# Pext is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Pext.

This is Pext's Settings class.

It lives in its own instance to prevent __main__.py and ui_qt5.py getting 2
different instances of it and thus not sharing settings.

This seems vaguely related to https://github.com/python/cpython/issues/71794.
"""

import configparser
import json
import os
import platform
import psutil
import sys
import time
import traceback

# Windows doesn't support getuid
if platform.system() == 'Windows':
    import getpass  # NOQA

from datetime import datetime
from distutils.util import strtobool
from pkg_resources import parse_version
from shutil import rmtree
from urllib.parse import quote_plus
try:
    from typing import Any, Dict, List, Optional, Union
except ImportError:
    from backports.typing import Any, Dict, List, Optional, Union  # type: ignore  # noqa: F401

import requests

from dulwich import porcelain
from dulwich.repo import Repo
from PyQt5.QtWidgets import QSystemTrayIcon

from pext.appfile import AppFile
from pext.configretriever import ConfigRetriever
from pext.enums import MinimizeMode, OutputMode, OutputSeparator
from pext.localemanager import LocaleManager
from pext.translation import Translation


class Logger():
    """Log events to the appropriate location.

    Shows events in the main window and, if the main window is not visible,
    as a desktop notification.
    """

    queued_messages = []  # type: List[Dict[str, str]]
    last_update = None  # type: Optional[float]

    window = None

    @staticmethod
    def bind_window(window: 'Window') -> None:  # type: ignore # noqa: F821
        """Give the logger the ability to log info to the main window."""
        Logger.window = window

    @staticmethod
    def _queue_message(module_name: str, message: str, type_name: str) -> None:
        """Queue a message for display."""
        for formatted_message in Logger._format_message(module_name, message):
            Logger.queued_messages.append(
                {'message': formatted_message, 'type': type_name})

    @staticmethod
    def _format_message(module_name: str, message: str) -> List[str]:
        """Format message for display, including splitting multiline messages."""
        message_lines = []
        for line in message.splitlines():
            if not (not line or line.isspace()):
                if module_name:
                    message = '{}: {}'.format(module_name, line)
                else:
                    message = line

                message_lines.append(message)

        return message_lines

    @staticmethod
    def _show_in_module(identifier: Optional[str], message: str) -> None:
        """Show in the module disabled screen."""
        if identifier and Logger.window:
            for tab_id, tab in enumerate(Logger.window.tab_bindings):  # type: ignore
                if tab.uiModule.metadata['id'] == identifier:
                    Logger.window.update_state(tab_id, message)

    @staticmethod
    def log(module_name: Optional[str], message: str, show_in_module=None) -> None:
        """If a logger is provided, log to the logger. Otherwise, print."""
        if Logger.window:
            if not module_name:
                module_name = ""

            Logger._queue_message(module_name, message, 'message')
            Logger._show_in_module(show_in_module, message)
        else:
            print(message)

    @staticmethod
    def log_error(module_name: Optional[str], message: str, show_in_module=None) -> None:
        """If a logger is provided, log to the logger. Otherwise, print."""
        if Logger.window:
            if not module_name:
                module_name = ""

            Logger._queue_message(module_name, message, 'error')
            Logger._show_in_module(show_in_module, message)
        else:
            print(message)

    @staticmethod
    def log_critical(module_name: Optional[str], message: str, detailed_message: Optional[str], metadata=None,
                     show_in_module=None) -> None:
        """If a window is provided, pop up a window. Otherwise, print."""
        if not module_name:
            module_name = ""
        if not detailed_message:
            detailed_message = ""

        if metadata and 'bugtracker' in metadata and 'bugtracker_type' in metadata:
            if metadata['bugtracker_type'] == "github":
                bugtracker_url = "".join([
                    metadata['bugtracker'],
                    "/issues/new?title=",
                    quote_plus(message),
                    "&body=Module%20version%20",
                    quote_plus(metadata['version']),
                    "%0APext%20",
                    quote_plus(UpdateManager().get_core_version()),
                    "%20on%20",
                    quote_plus(sys.platform),
                    "%0A%0A",
                    "```%0A",
                    quote_plus(detailed_message),
                    "```"
                ])
            else:
                bugtracker_url = metadata['bugtracker']
        else:
            bugtracker_url = ""

        if Logger.window and module_name:
            Logger.window.add_actionable(
                "module_error_{}".format(module_name),
                Translation.get("actionable_error_in_module").format(module_name, message),
                Translation.get("actionable_report_error_in_module") if bugtracker_url else "",
                bugtracker_url)
            Logger._show_in_module(show_in_module, detailed_message)

        print("{}\n{}\n{}".format(module_name if module_name else "Pext", message, detailed_message))

    @staticmethod
    def show_next_message() -> None:
        """Show next statusbar message.

        Display the next message. If no more messages are available, clear the
        status bar after it has been displayed for 5 seconds.
        """
        if not Logger.window:
            return

        current_time = time.time()

        if len(Logger.queued_messages) == 0:
            if not Logger.last_update or current_time - 5 > Logger.last_update:
                Logger.window.set_status_text("")
                Logger.last_update = None
        else:
            message = Logger.queued_messages.pop(0)

            if message['type'] == 'error':
                statusbar_message = "<font color='red'>⚠ {}</color>".format(message['message'])
                icon = QSystemTrayIcon.Warning
            else:
                statusbar_message = message['message']
                icon = QSystemTrayIcon.Information

            Logger.window.set_status_text(statusbar_message)

            if Logger.window.tray:
                Logger.window.tray.tray.showMessage('Pext', message['message'], icon)

            Logger.last_update = current_time


class ObjectManager():
    """Shared management for modules and themes."""

    @staticmethod
    def list_object(full_path: str) -> Optional[Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return the identifier, name, source and metadata of an object."""
        if not os.path.isdir(full_path):
            return None

        location = os.path.basename(full_path)

        try:
            source = UpdateManager.get_remote_url(full_path)  # type: Optional[str]
        except Exception:
            source = None

        try:
            with open(os.path.join(full_path, "metadata.json"), 'r') as metadata_json:
                metadata = json.load(metadata_json)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Object {} lacks a correctly formatted metadata.json file".format(location))
            return None

        try:
            with open(os.path.join(full_path, "metadata_{}.json".format(
                      LocaleManager.find_best_locale(Settings.get('locale')).name())), 'r') as metadata_json_i18n:
                metadata.update(json.load(metadata_json_i18n))
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Object {} has no metadata_{}.json file".format(location,
                  LocaleManager.find_best_locale(Settings.get('locale')).name()))

        # Ensure the required metadata is set
        if 'id' not in metadata:
            print("Object {} lacks required field id".format(location))
            return None

        if 'name' not in metadata:
            print("Object {} lacks required field name".format(location))
            return None

        # Ensure the location makes sense
        if location != metadata['id'].replace('.', '_'):
            print("Object {}'s location is not correct for identifier {}".format(location, metadata['id']))
            return None

        # Add revision last updated time
        if source:
            try:
                version = UpdateManager.get_version(full_path)
                metadata['version'] = version
            except Exception:
                pass

            try:
                last_updated = UpdateManager.get_last_updated(full_path)
                metadata['last_updated'] = str(last_updated)
            except Exception:
                pass

        return {"source": source, "metadata": metadata}

    @staticmethod
    def list_objects(core_directory: str) -> Dict[str, Dict[str, Optional[Union[str, Dict[str, str]]]]]:
        """Return a list of objects together with their identifier, name, source and metadata."""
        objects = {}

        for directory in os.listdir(core_directory):
            dir_object = ObjectManager.list_object(os.path.join(core_directory, directory))
            if dir_object and isinstance(dir_object['metadata'], dict) and 'id' in dir_object['metadata']:
                object_id = dir_object['metadata']['id']
                objects[object_id] = dir_object

        return objects


class ProfileManager():
    """Create, remove, list, load and save to a profile."""

    def __init__(self) -> None:
        """Initialize the profile manager."""
        self.profile_dir = os.path.join(ConfigRetriever.get_path(), 'profiles')
        self.module_dir = os.path.join(ConfigRetriever.get_path(), 'modules')
        self.saved_settings = ['_window_geometry',
                               'turbo_mode',
                               'locale',
                               'minimize_mode',
                               'output_mode',
                               'output_separator',
                               'theme',
                               'tray',
                               'global_hotkey_enabled',
                               'last_update_check',
                               'update_check',
                               'object_update_check',
                               'object_update_install']

    @staticmethod
    def _get_pid_path(profile: str) -> str:
        if platform.system() == 'Windows':
            uid = getpass.getuser()
        else:
            uid = str(os.getuid())

        return os.path.join(ConfigRetriever.get_temp_path(), '{}_pext_{}.pid'.format(uid, profile))

    @staticmethod
    def lock_profile(profile: str) -> None:
        """Claim the profile as in-use."""
        pidfile = ProfileManager._get_pid_path(profile)
        pid = str(os.getpid())
        open(pidfile, 'w').write(pid)

    @staticmethod
    def get_lock_instance(profile: str) -> Optional[int]:
        """Get the pid of the current process having a lock, if any."""
        pidfile = ProfileManager._get_pid_path(profile)
        if not os.path.isfile(pidfile):
            return None

        pid = int(open(pidfile, 'r').read())

        if not psutil.pid_exists(pid):
            return None

        return pid

    @staticmethod
    def unlock_profile(profile: str) -> None:
        """Remove the status of the profile currently being in use."""
        pidfile = ProfileManager._get_pid_path(profile)
        os.unlink(pidfile)

    @staticmethod
    def default_profile_name() -> str:
        """Return the default profile name."""
        return "default"

    def create_profile(self, profile: str) -> bool:
        """Create a new empty profile if name not in use already."""
        try:
            os.mkdir(os.path.join(self.profile_dir, profile))
        except OSError:
            return False

        return True

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile that's currently not in use, if the new name doesn't already exist."""
        if ProfileManager.get_lock_instance(old_name):
            return False

        try:
            os.rename(os.path.join(self.profile_dir, old_name), os.path.join(self.profile_dir, new_name))
        except OSError:
            return False

        return True

    def remove_profile(self, profile: str) -> bool:
        """Remove a profile and all associated data if not in use."""
        if ProfileManager.get_lock_instance(profile):
            return False

        rmtree(os.path.join(self.profile_dir, profile))
        return True

    def list_profiles(self) -> List[str]:
        """List the existing profiles."""
        return os.listdir(self.profile_dir)

    def save_modules(self, profile: str, modules: List['UiModule']) -> None:  # type: ignore # noqa: F821
        """Save the list of open modules and their settings to the profile."""
        config = configparser.ConfigParser()
        for number, module in enumerate(modules):
            settings = {}
            for setting in module.settings:
                # Only save non-internal variables
                if setting[0] != "_":
                    value = module.settings[setting]
                    settings[setting] = str(value) if value is not None else ''

            # Append Pext state variables
            for setting in module.vm.settings:
                try:
                    value = module.vm.settings[setting].name
                except KeyError:
                    value = module.vm.settings[setting]

                settings[setting] = str(value) if value is not None else ''

            config['{}_{}'.format(number, module.metadata['id'])] = settings

        with open(os.path.join(self.profile_dir, profile, 'modules'), 'w') as configfile:
            config.write(configfile)

    def retrieve_modules(self, profile: str) -> List[Dict]:
        """Retrieve the list of modules and their settings from the profile."""
        config = configparser.ConfigParser()
        modules = []

        config.read(os.path.join(self.profile_dir, profile, 'modules'))

        for module in config.sections():
            identifier = module.split('_', 1)[1]
            data = ObjectManager.list_object(os.path.join(self.module_dir, identifier.replace('.', '_')))
            if not data:
                # Module no longer seems to exist, skip
                continue

            settings = {}

            for key in config[module]:
                settings[key] = config[module][key]

            modules.append({'metadata': data['metadata'], 'settings': settings})

        return modules

    def save_settings(self, profile: Optional[str], changed_key: Optional[str] = None) -> None:
        """Save the current settings to the profile."""
        if changed_key and changed_key not in self.saved_settings:
            return

        config = configparser.ConfigParser()
        settings_to_store = {}
        for setting in Settings.get_all(profile if profile else None):
            if setting in self.saved_settings:
                setting_data = Settings.get(setting)
                try:
                    setting_data = setting_data.value
                except AttributeError:
                    pass
                if setting_data is not None and setting_data != "":
                    settings_to_store[setting] = setting_data

        config['settings'] = settings_to_store

        if profile:
            path = os.path.join(self.profile_dir, profile, 'settings')
        else:
            path = os.path.join(ConfigRetriever.get_path(), 'settings')

        with open(path, 'w') as configfile:
            config.write(configfile)

    def retrieve_settings(self, profile: Optional[str]) -> Dict[str, Any]:
        """Retrieve the settings from the profile."""
        config = configparser.ConfigParser()
        setting_dict = {}  # type: Dict[str, Any]

        if profile:
            path = os.path.join(self.profile_dir, profile, 'settings')
        else:
            path = os.path.join(ConfigRetriever.get_path(), 'settings')

        config.read(path)

        try:
            for setting in config['settings']:
                if setting in self.saved_settings:
                    setting_value = config['settings'][setting]  # type: Any
                    try:
                        setting_value = bool(strtobool(setting_value.lower()))
                    except ValueError:
                        pass
                    setting_dict[setting] = setting_value
        except KeyError:
            pass

        return setting_dict


class Settings():
    """A globally accessible class that stores all Pext's settings."""

    __settings = {
        '_launch_app': True,  # Keep track if launching is normal
        '_window_geometry': None,
        '_portable': False,
        '_force_module_branch_type': None,  # TODO: Remove in favor of a proper per-module selection
        'background': False,
        'turbo_mode': False,
        'locale': None,
        'modules': [],
        'minimize_mode': MinimizeMode.Normal if platform.system() == "Darwin" else MinimizeMode.Tray,
        'profile': ProfileManager.default_profile_name(),
        'output_mode': OutputMode.DefaultClipboard,
        'output_separator': OutputSeparator.Enter,
        'style': None,
        'theme': None,
        'global_hotkey_enabled': True,
        'tray': True
    }  # type: Dict[str, Any]

    __global_settings = {
        'last_update_check': None,
        'update_check': None,  # None = not asked, True/False = permission
        'object_update_check': None,  # None = not asked, True/False = permission
        'object_update_install': True  # True/False = permission
    }

    @staticmethod
    def get(name, default=None):
        """Return the value of a single setting, falling back to default if None."""
        try:
            value = Settings.__global_settings[name]
            if value is None:
                return default

            return value
        except KeyError:
            pass

        try:
            value = Settings.__settings[name]
        except KeyError:
            value = None

        if value is None:
            return default

        return value

    @staticmethod
    def get_all(profile=None):
        """Return all settings."""
        if profile:
            return Settings.__settings
        else:
            return Settings.__global_settings

    @staticmethod
    def set(name, value):
        """Set a single setting if this setting is known."""
        if name in Settings.__global_settings:
            profile = None
        else:
            profile = Settings.get('profile')
            if name not in Settings.__settings:
                raise NameError('{} is not a key of Settings'.format(name))

        if Settings.get(name) == value:
            return

        if name in Settings.__global_settings:
            Settings.__global_settings[name] = value
        else:
            Settings.__settings[name] = value

        ProfileManager().save_settings(profile, changed_key=name)

    @staticmethod
    def update(value):
        """Update the dictionary with new values if any changed."""
        Settings.__settings.update(value)

    @staticmethod
    def update_global(value):
        """Update the globals dictionary with new values if any changed."""
        Settings.__global_settings.update(value)


class UpdateManager():
    """Manages scheduling and checking automatic updates."""

    def __init__(self) -> None:
        """Initialize the UpdateManager and store the version info of Pext."""
        self.version = "Unknown"
        version = None
        try:
            version = UpdateManager.get_version(os.path.dirname(AppFile.get_path()))
        except Exception:
            pass

        if not version:
            with open(os.path.join(AppFile.get_path(), 'VERSION')) as version_file:
                version = version_file.read().strip()

        if version:
            self.version = version

    @staticmethod
    def _path_to_repo(directory: str) -> Repo:
        return Repo(directory)

    def get_core_version(self) -> str:
        """Return the version info of Pext itself."""
        return self.version

    @staticmethod
    def fix_git_url_for_dulwich(url: str) -> str:
        """Append .git to the URL to work around a Dulwich + GitHub issue.

        Dulwich before 0.18.4 sends an user agent GitHub doesn't respond to correctly.
        """
        if url.startswith("https://") and not url.endswith(".git"):
            url += ".git"

        return url

    @staticmethod
    def get_wanted_branch_from_metadata(metadata: Dict[Any, Any], identifier: str) -> bytes:
        """Get the wanted branch from the given metadata.json."""
        branch_type = "stable"
        if Settings.get('_force_module_branch_type'):
            branch_type = Settings.get('_force_module_branch_type')

        try:
            branch = metadata["git_branch_{}".format(branch_type)]
        except (IndexError, KeyError, json.decoder.JSONDecodeError):
            print("Couldn't figure out branch for type {} of {}, defaulting to master".format(branch_type, identifier))
            return "refs/heads/master".encode()

        return "refs/heads/{}".format(branch).encode()

    @staticmethod
    def get_wanted_branch(directory: str) -> bytes:
        """Get the wanted branch from the metadata.json for this git object."""
        try:
            with open(os.path.join(directory, "metadata.json"), 'r') as metadata_json:
                branch = UpdateManager.get_wanted_branch_from_metadata(json.load(metadata_json), directory)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print("Couldn't figure out branch for {}, defaulting to master".format(directory))
            return "refs/heads/master".encode()

        return branch

    @staticmethod
    def get_remote_url(directory: str) -> str:
        """Get the url of the given remote for the specified git-managed directory."""
        with UpdateManager._path_to_repo(directory) as repo:
            config = repo.get_config()
            return config.get(("remote".encode(), "origin".encode()), "url".encode()).decode()

    @staticmethod
    def ensure_repo_branch(directory: str, branch: bytes) -> None:
        """Check if an update is available for the git-managed directory."""
        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            # Get current branch
            current_branch = repo.refs.get_symrefs()[b"HEAD"]

            if current_branch != branch:
                # Update to wanted branch
                remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
                try:
                    porcelain.pull(repo, remote_url, branch, force=True)
                    # Ensure a clean state on the wanted branch
                    repo.reset_index(repo[branch].tree)
                    repo.refs.set_symbolic_ref(b"HEAD", branch)
                except KeyError as e:
                    Logger.log_error(None, Translation.get("failed_to_checkout_branch").format(directory, e))
                    traceback.print_exc()

    @staticmethod
    def has_update(directory: str, branch=None) -> bool:
        """Check if an update is available for the git-managed directory."""
        if branch is None:
            branch = UpdateManager.get_wanted_branch(directory)

        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            UpdateManager.ensure_repo_branch(directory, branch)

            old_commit = repo[repo.head()]
            remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
            try:
                remote_commit = porcelain.ls_remote(remote_url)[branch]
            except Exception as e:
                Logger.log_error(None, Translation.get("failed_to_check_for_module_update").format(directory, e))
                traceback.print_exc()

                return False

            return remote_commit != old_commit.id

    @staticmethod
    def update(directory: str) -> bool:
        """If an update is available, attempt to update the git-managed directory."""
        # Get current commit
        with UpdateManager._path_to_repo(directory) as repo:
            old_commit = repo[repo.head()]

            # Update
            remote_url = UpdateManager.fix_git_url_for_dulwich(UpdateManager.get_remote_url(directory))
            porcelain.pull(repo, remote_url, force=True)

            # See if anything was updated
            return old_commit != repo[repo.head()]

    @staticmethod
    def get_version(directory: str) -> Optional[str]:
        """Get the version of the git-managed directory."""
        return porcelain.describe(directory)

    @staticmethod
    def get_last_updated(directory: str) -> Optional[datetime]:
        """Return the time of the latest update of the git-managed directory."""
        with UpdateManager._path_to_repo(directory) as repo:
            commit = repo[repo.head()]
            return datetime.fromtimestamp(commit.commit_time)

    def check_core_update(self) -> Optional[str]:
        """Check if there is an update of the core and if so, return the name of the new version."""
        # Normalize own version
        if self.version.find('+dev') != -1:
            version = self.version[:self.version.find('+dev')]
        else:
            version = self.version

        if self.version.find('-') != -1:
            available_version = requests.get('https://pext.io/version/nightly').text.splitlines()[0].strip()
        else:
            available_version = requests.get('https://pext.io/version/stable').text.splitlines()[0].strip()

        if parse_version(version.lstrip('v')) < parse_version(available_version.lstrip('v')):
            return available_version

        return None
