#!/usr/bin/env python3

# Copyright (c) 2015 - 2020 Sylvia van Os <sylvia@hackerchick.me>
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

This is Pext's Qt5 Gui.
"""

import os
import platform
import sys
import threading
import time
import traceback
import webbrowser

from copy import copy
from functools import partial
from inspect import signature
try:
    from typing import Any, Callable, Dict, List, Optional, Set, Union
except ImportError:
    from backports.typing import Any, Callable, Dict, List, Optional, Set, Union  # type: ignore  # noqa: F401
from queue import Queue
from shutil import copytree, rmtree
from subprocess import Popen

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QAction, QMenu, QSystemTrayIcon
from PyQt5.Qt import (QClipboard, QIcon, QObject, QStringListModel, QQmlApplicationEngine, QQmlComponent, QQmlContext,
                      QQmlProperty, QUrl)
from PyQt5.QtGui import QWindow

from pext.__main__ import (AppFile, ConfigRetriever, Core, InternalCallProcessor, LocaleManager, Logger, ModuleManager,
                           MinimizeMode, OutputMode, OutputSeparator, ProfileManager, RunConseq, Settings, SortMode,
                           ThemeManager, Translation, UiModule, UpdateManager)
from constants import USE_INTERNAL_UPDATER

from pext_helpers import Selection  # noqa: E402

pyautogui_error = None
if platform.system() == 'Darwin':
    # https://github.com/moses-palmer/pynput/issues/83#issuecomment-410264758
    try:
        from pyautogui import hotkey, typewrite
    except Exception:
        pyautogui_error = traceback.format_exc()
        traceback.print_exc()

pynput_error = None
try:
    from pynput import keyboard
except Exception:
    pynput_error = traceback.format_exc()
    traceback.print_exc()

# FIXME: Workaround for https://bugs.launchpad.net/ubuntu/+source/python-qt4/+bug/941826
warn_no_openGL_linux = False
if platform.system() == "Linux":
    try:
        from OpenGL import GL  # NOQA
    except ImportError:
        warn_no_openGL_linux = True
    except Exception as e:
        print('Could not import OpenGL module: {}'.format(e))
        traceback.print_exc()
        print("python3-opengl is not installed. If Pext fails to render, please try installing it. "
              "See https://github.com/Pext/Pext/issues/11.")


class WindowModule():
    """A model's state in the window."""

    def __init__(self, window: 'Window', uiModule: UiModule, module_context: QQmlContext, tab_data,
                 result_list_model_list: QStringListModel, context_menu_model_list: QStringListModel,
                 context_menu_list_full: QStringListModel) -> None:
        """Initialize the WindowModule."""
        self.window = window
        self.uiModule = uiModule
        self.context = module_context
        self.tab_data = tab_data
        self.result_list_model_list = result_list_model_list
        self.context_menu_model_list = context_menu_model_list
        self.context_menu_model_list_full = context_menu_model_list

    def bind_header_text(self, header_text: QObject):
        """Bind the header text object to the WindowModule."""
        self.header_text = header_text

    def bind_result_list_model(self, result_list_model: QObject):
        """Bind the result list model object to the WindowModule."""
        self.result_list_model = result_list_model

    def bind_base_info_panel(self, base_info_panel: QObject):
        """Bind the base info panel object to the WindowModule."""
        self.base_info_panel = base_info_panel

    def bind_context_info_panel(self, context_info_panel: QObject):
        """Bind the context info panel object to the WindowModule."""
        self.context_info_panel = context_info_panel

    def bind_context_menu_model(self, context_menu_model: QObject):
        """Bind the context menu model object to the WindowModule."""
        self.context_menu_model = context_menu_model

    def search_string_changed(self, search_string: str) -> None:
        """Update the UI when the search string changes."""
        QQmlProperty.write(self.window.search_input_model, "text", search_string)
        self.context.setContextProperty("searchInputFieldEmpty", False if search_string else True)

    def result_list_changed(self, entries: List[str], normal_count: int, command_count: int,
                            unfiltered_entry_count: int) -> None:
        """Update the UI when the result list changes."""
        self.result_list_model_list.setStringList(str(entry) for entry in entries)
        self.context.setContextProperty("resultListModelNormalEntries", normal_count)
        self.context.setContextProperty("resultListModelCommandEntries", command_count)
        self.context.setContextProperty("resultListModelHasEntries", True if unfiltered_entry_count else False)

    def result_list_index_changed(self, index: int) -> None:
        """Update the UI when the result list index changes."""
        QQmlProperty.write(self.result_list_model, "currentIndex", index)

    def context_menu_enabled_changed(self, value: bool) -> None:
        """Update the UI when the context menu gets enabled or disabled."""
        self.context.setContextProperty("contextMenuEnabled", value)

    def context_menu_index_changed(self, index: int) -> None:
        """Update the UI when the context menu index changes."""
        QQmlProperty.write(self.context_menu_model, "currentIndex", index)

    def context_menu_list_changed(self, base: List[str], entry_specific: List[str]) -> None:
        """Update the UI when the context menu list changes."""
        self.context_menu_model_list.setStringList(str(entry) for entry in entry_specific)
        combined_list = entry_specific + base
        self.context_menu_model_list_full.setStringList(str(entry) for entry in combined_list)

        self.context.setContextProperty("contextMenuModel", self.context_menu_model_list)
        self.context.setContextProperty("contextMenuModelFull", self.context_menu_model_list_full)
        self.context.setContextProperty("contextMenuModelEntrySpecificCount", len(entry_specific))

    def context_info_panel_changed(self, value: str) -> None:
        """Update the UI when the context info panel changes."""
        QQmlProperty.write(self.context_info_panel, "text", value)

    def base_info_panel_changed(self, value: str) -> None:
        """Update the UI when the base info panel changes."""
        QQmlProperty.write(self.base_info_panel, "text", value)

    def sort_mode_changed(self, sort_mode: SortMode) -> None:
        """Update the UI when the sort mode changes."""
        self.context.setContextProperty("sortMode", str(sort_mode))

    def unprocessed_count_changed(self, count: int) -> None:
        """Update the UI when the unprocessed change count changes."""
        self.context.setContextProperty("unprocessedCount", count)

    def selection_changed(self, selection: List[Selection]) -> None:
        """Update the UI when the user selection tree changes."""
        # Normalize for display in the tree list, fixes QML displaying things like QVariant instead of text
        normalized_selection = []
        for entry in selection:
            normalized_entry = copy(entry)
            normalized_entry.value = str(normalized_entry.value)
            if normalized_entry.context_option is not None:
                normalized_entry.context_option = str(normalized_entry.context_option)
            normalized_selection.append(vars(normalized_entry))

        self.context.setContextProperty("resultListModelTree", normalized_selection)

    def header_text_changed(self, value: str) -> None:
        """Update the UI when the header text changes."""
        QQmlProperty.write(self.header_text, "text", value)

    def update_result_list_index(self) -> None:
        """Update the ViewModel's result list index."""
        self.uiModule.vm.update_result_list_index(QQmlProperty.read(self.result_list_model, "currentIndex"))

    def update_context_menu_index(self) -> None:
        """Update the ViewModel's context menu index."""
        self.uiModule.vm.update_context_menu_index(QQmlProperty.read(self.context_menu_model, "currentIndex"))


class Window():
    """The main Pext window."""

    def __init__(self, app: QApplication, locale_manager: LocaleManager, module_manager: ModuleManager,
                 theme_manager: 'ThemeManager', parent=None) -> None:
        """Initialize the window."""
        # Actionable items to show in the UI
        self.actionables = []  # type: List[Dict]

        # Text to type on close if needed
        self.output_queue = []  # type: List[str]

        # Save settings
        self.locale_manager = locale_manager

        self.tab_bindings = []  # type: List[WindowModule]
        self.tray = None  # type: Optional[Tray]

        self.app = app
        self.engine = QQmlApplicationEngine(None)

        # Set QML variables
        self.context = self.engine.rootContext()
        self.context.setContextProperty(
            "FORCE_FULLSCREEN", self.app.platformName() in ['webgl', 'vnc'])
        self.context.setContextProperty(
            "USE_INTERNAL_UPDATER", USE_INTERNAL_UPDATER)
        self.context.setContextProperty(
            "applicationVersion", UpdateManager().get_core_version())
        self.context.setContextProperty(
            "systemPlatform", platform.system())

        self.context.setContextProperty(
            "modulesPath", os.path.join(ConfigRetriever.get_path(), 'modules'))
        self.context.setContextProperty(
            "themesPath", os.path.join(ConfigRetriever.get_path(), 'themes'))

        self.context.setContextProperty("currentTheme", Settings.get('theme'))
        self.context.setContextProperty("defaultProfile", ProfileManager.default_profile_name())
        self.context.setContextProperty("currentProfile", Settings.get('profile'))
        self.context.setContextProperty("currentLocale", self.locale_manager.get_current_locale(system_if_unset=False))
        self.context.setContextProperty("currentLocaleCode",
                                        LocaleManager.find_best_locale(Settings.get('locale')).name())
        self.context.setContextProperty("locales", self.locale_manager.get_locales())

        # Prepare dependencies for the main UI
        self.module_manager = module_manager
        self.theme_manager = theme_manager
        self.profile_manager = ProfileManager()

        # Load the main UI
        self.engine.objectCreated.connect(self._bind_to_loaded_ui)
        self.engine.load(QUrl.fromLocalFile(os.path.join(AppFile.get_path(), 'qml', 'main.qml')))

    def _bind_to_loaded_ui(self, object: QObject, url: QUrl):
        self.window = self.engine.rootObjects()[0]

        # Give the translator a reference to the window
        Translation.bind_window(self)

        # Some hacks to make Qt WebGL streaming work
        if self.app.platformName() == 'webgl':
            self.parent_window = QWindow()
            self.parent_window.setVisibility(QWindow.FullScreen)
            self.window.setParent(self.parent_window)

        # Override quit and minimize
        self.window.confirmedClose.connect(self.quit)
        self.window.windowStateChanged.connect(self._process_window_state)

        # Give QML the module info
        self.intro_screen = self.window.findChild(QObject, "introScreen")
        self._update_modules_info_qml()

        # Give QML the theme info
        self._update_themes_info_qml()

        # Give QML the profile info
        self._update_profiles_info_qml()

        # Bind global shortcuts
        self.search_input_model = self.window.findChild(
            QObject, "searchInputModel")
        escape_shortcut = self.window.findChild(QObject, "escapeShortcut")
        shift_escape_shortcut = self.window.findChild(QObject, "shiftEscapeShortcut")
        back_button = self.window.findChild(QObject, "backButton")
        tab_shortcut = self.window.findChild(QObject, "tabShortcut")
        args_shortcut = self.window.findChild(QObject, "argsShortcut")

        self.search_input_model.textChanged.connect(self._search)
        self.search_input_model.accepted.connect(self._select)
        escape_shortcut.activated.connect(self._go_up)
        shift_escape_shortcut.activated.connect(self._go_up_to_base_and_minimize)
        back_button.clicked.connect(self._go_up)
        tab_shortcut.activated.connect(self._tab_complete)
        args_shortcut.activated.connect(self._input_args)

        # Bind internal calls
        self.window.internalCall.connect(InternalCallProcessor.enqueue)

        # Bind actionable remove
        actionable_repeater = self.window.findChild(
            QObject, "actionableRepeater")
        actionable_repeater.removeActionable.connect(self._remove_actionable)

        # Find menu entries
        menu_reload_active_module_shortcut = self.window.findChild(
            QObject, "menuReloadActiveModule")
        self.menu_load_module_shortcut = self.window.findChild(
            QObject, "menuLoadModule")
        menu_close_active_module_shortcut = self.window.findChild(
            QObject, "menuCloseActiveModule")
        menu_install_module_shortcut = self.window.findChild(
            QObject, "menuInstallModule")
        menu_manage_modules_shortcut = self.window.findChild(
            QObject, "menuManageModules")

        menu_load_theme_shortcut = self.window.findChild(
            QObject, "menuLoadTheme")
        menu_install_theme_shortcut = self.window.findChild(
            QObject, "menuInstallTheme")
        menu_manage_themes_shortcut = self.window.findChild(
            QObject, "menuManageThemes")

        menu_load_profile_shortcut = self.window.findChild(
            QObject, "menuLoadProfile")
        menu_manage_profiles_shortcut = self.window.findChild(
            QObject, "menuManageProfiles")

        menu_turbo_mode_shortcut = self.window.findChild(
            QObject, "menuTurboMode")

        menu_change_language_shortcut = self.window.findChild(
            QObject, "menuChangeLanguage")

        self.menu_output_default_clipboard = self.window.findChild(
            QObject, "menuOutputDefaultClipboard")
        menu_output_selection_clipboard = self.window.findChild(
            QObject, "menuOutputSelectionClipboard")
        menu_output_find_buffer = self.window.findChild(
            QObject, "menuOutputFindBuffer")
        self.menu_output_auto_type = self.window.findChild(
            QObject, "menuOutputAutoType")

        menu_output_separator_none = self.window.findChild(
            QObject, "menuOutputSeparatorNone")
        menu_output_separator_enter = self.window.findChild(
            QObject, "menuOutputSeparatorEnter")
        menu_output_separator_tab = self.window.findChild(
            QObject, "menuOutputSeparatorTab")

        menu_minimize_normally_shortcut = self.window.findChild(
            QObject, "menuMinimizeNormally")
        menu_minimize_to_tray_shortcut = self.window.findChild(
            QObject, "menuMinimizeToTray")
        menu_minimize_normally_manually_shortcut = self.window.findChild(
            QObject, "menuMinimizeNormallyManually")
        menu_minimize_to_tray_manually_shortcut = self.window.findChild(
            QObject, "menuMinimizeToTrayManually")
        self.menu_enable_global_hotkey_shortcut = self.window.findChild(
            QObject, "menuEnableGlobalHotkey")
        menu_show_tray_icon_shortcut = self.window.findChild(
            QObject, "menuShowTrayIcon")
        menu_install_quick_action_service = self.window.findChild(
            QObject, "menuInstallQuickActionService")
        self.menu_enable_update_check_shortcut = self.window.findChild(
            QObject, "menuEnableUpdateCheck")
        self.menu_enable_object_update_check_shortcut = self.window.findChild(
            QObject, "menuEnableObjectUpdateCheck")
        self.menu_enable_object_update_install_shortcut = self.window.findChild(
            QObject, "menuEnableObjectUpdateInstall")

        menu_quit_shortcut = self.window.findChild(QObject, "menuQuit")
        menu_check_for_updates_shortcut = self.window.findChild(QObject, "menuCheckForUpdates")
        menu_homepage_shortcut = self.window.findChild(QObject, "menuHomepage")

        # Bind menu entries
        menu_reload_active_module_shortcut.triggered.connect(
            self._reload_active_module)
        self.menu_load_module_shortcut.loadModuleRequest.connect(self._open_tab)
        menu_close_active_module_shortcut.triggered.connect(self._close_tab)
        menu_install_module_shortcut.installModuleRequest.connect(
            self._menu_install_module)
        menu_manage_modules_shortcut.uninstallModuleRequest.connect(
            self._menu_uninstall_module)
        menu_manage_modules_shortcut.updateModuleRequest.connect(self._menu_update_module)

        menu_load_theme_shortcut.loadThemeRequest.connect(self._menu_switch_theme)
        menu_install_theme_shortcut.installThemeRequest.connect(
            self._menu_install_theme)
        menu_manage_themes_shortcut.uninstallThemeRequest.connect(
            self._menu_uninstall_theme)
        menu_manage_themes_shortcut.updateThemeRequest.connect(self._menu_update_theme)

        menu_load_profile_shortcut.loadProfileRequest.connect(self._menu_switch_profile)
        menu_manage_profiles_shortcut.createProfileRequest.connect(self._menu_create_profile)
        menu_manage_profiles_shortcut.renameProfileRequest.connect(self._menu_rename_profile)
        menu_manage_profiles_shortcut.removeProfileRequest.connect(self._menu_remove_profile)

        menu_turbo_mode_shortcut.toggled.connect(self._menu_toggle_turbo_mode)

        menu_change_language_shortcut.changeLanguage.connect(self._menu_change_language)

        self.menu_output_default_clipboard.toggled.connect(self._menu_output_default_clipboard)
        menu_output_selection_clipboard.toggled.connect(self._menu_output_selection_clipboard)
        menu_output_find_buffer.toggled.connect(self._menu_output_find_buffer)
        self.menu_output_auto_type.toggled.connect(self._menu_output_auto_type)

        menu_output_separator_none.toggled.connect(self._menu_output_separator_none)
        menu_output_separator_enter.toggled.connect(self._menu_output_separator_enter)
        menu_output_separator_tab.toggled.connect(self._menu_output_separator_tab)

        menu_minimize_normally_shortcut.toggled.connect(self._menu_minimize_normally)
        menu_minimize_to_tray_shortcut.toggled.connect(self._menu_minimize_to_tray)
        menu_minimize_normally_manually_shortcut.toggled.connect(self._menu_minimize_normally_manually)
        menu_minimize_to_tray_manually_shortcut.toggled.connect(self._menu_minimize_to_tray_manually)
        self.menu_enable_global_hotkey_shortcut.toggled.connect(self._menu_enable_global_hotkey_shortcut)
        menu_show_tray_icon_shortcut.toggled.connect(self._menu_toggle_tray_icon)
        menu_install_quick_action_service.triggered.connect(self._menu_install_quick_action_service)
        self.menu_enable_object_update_check_shortcut.toggled.connect(self._menu_toggle_object_update_check)
        self.menu_enable_object_update_install_shortcut.toggled.connect(self._menu_toggle_object_update_install)

        menu_quit_shortcut.triggered.connect(self.quit)
        menu_check_for_updates_shortcut.triggered.connect(self._menu_check_updates)
        menu_homepage_shortcut.triggered.connect(self._show_homepage)

        # Set entry states
        QQmlProperty.write(menu_turbo_mode_shortcut,
                           "checked",
                           Settings.get('turbo_mode'))

        QQmlProperty.write(self.menu_output_default_clipboard,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.DefaultClipboard)
        QQmlProperty.write(menu_output_selection_clipboard,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.SelectionClipboard)
        QQmlProperty.write(menu_output_find_buffer,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.FindBuffer)
        QQmlProperty.write(self.menu_output_auto_type,
                           "checked",
                           int(Settings.get('output_mode')) == OutputMode.AutoType)

        QQmlProperty.write(menu_output_separator_none,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.None_)
        QQmlProperty.write(menu_output_separator_enter,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.Enter)
        QQmlProperty.write(menu_output_separator_tab,
                           "checked",
                           int(Settings.get('output_separator')) == OutputSeparator.Tab)

        QQmlProperty.write(menu_minimize_normally_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.Normal)
        QQmlProperty.write(menu_minimize_to_tray_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.Tray)
        QQmlProperty.write(menu_minimize_normally_manually_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.NormalManualOnly)
        QQmlProperty.write(menu_minimize_to_tray_manually_shortcut,
                           "checked",
                           int(Settings.get('minimize_mode')) == MinimizeMode.TrayManualOnly)

        QQmlProperty.write(self.menu_enable_global_hotkey_shortcut,
                           "checked",
                           Settings.get('global_hotkey_enabled'))
        QQmlProperty.write(menu_show_tray_icon_shortcut,
                           "checked",
                           Settings.get('tray'))
        QQmlProperty.write(self.menu_enable_update_check_shortcut,
                           "checked",
                           Settings.get('update_check'))
        QQmlProperty.write(self.menu_enable_object_update_check_shortcut,
                           "checked",
                           Settings.get('object_update_check'))
        QQmlProperty.write(self.menu_enable_object_update_install_shortcut,
                           "checked",
                           Settings.get('object_update_check') and Settings.get('object_update_install'))

        # Get module user communication dialogs
        self.args_request = self.window.findChild(QObject, "commandArgsDialog")
        self.question_dialog = self.window.findChild(QObject, "questionDialog")
        self.choice_dialog = self.window.findChild(QObject, "choiceDialog")
        self.input_request = self.window.findChild(QObject, "inputRequests")

        # Get status text
        self.status_text = self.window.findChild(QObject, "statusText")

        # We bind the update check after writing the initial value to prevent
        # instantly triggering the update check
        self.menu_enable_update_check_shortcut.toggled.connect(self._menu_toggle_update_check)

        # Get reference to tabs list
        self.tabs = self.window.findChild(QObject, "tabs")

        # Bind the context when the tab is loaded
        self.tabs.currentIndexChanged.connect(self._bind_context)

        # Update active module when the tab is changed
        self.tabs.currentIndexChanged.connect(self._update_active_module)

        # Show the window if not --background
        if platform.system() == 'Darwin' and Settings.get('background'):
            # workaround for https://github.com/Pext/Pext/issues/20
            # First, we showMinimized to prevent Pext from being unrestorable
            self.window.showMinimized()
            # Then, we tell macOS to give the focus back to the last app
            self._macos_focus_workaround()
        elif not Settings.get('background'):
            self.show()

            if Settings.get('update_check') is None and USE_INTERNAL_UPDATER:
                # Tell the user automatic updating is enabled but set the last
                # check to right now so the user can disable it before the first
                # check
                Settings.set('last_update_check', time.time())
                self.add_actionable("update_check_enabled", Translation.get("actionable_update_check_enabled"))

                self._menu_toggle_object_update_check(True)
                self._menu_toggle_object_update_install(True)
                self._menu_toggle_update_check(True)

        # Set remembered geometry
        if not self.app.platformName() in ['webgl', 'vnc']:
            geometry = Settings.get('_window_geometry')
            try:
                self.window.setGeometry(*[int(geopoint) for geopoint in geometry.split(';')])
            except Exception as e:
                if geometry:
                    print("Invalid geometry: {}".format(e))
                screen_size = self.window.screen().size()
                self.window.setGeometry((screen_size.width() - 800) // 2, (screen_size.height() - 600) // 2, 800, 600)

        # Start binding the modules
        if len(Settings.get('modules')) > 0:
            for module in Settings.get('modules'):
                self.module_manager.load(module, None, self)
        else:
            for module in ProfileManager().retrieve_modules(Settings.get('profile')):
                self.module_manager.load(module, None, self)

        # If there's only one module passed through the command line, enforce
        # loading it now. Otherwise, switch back to the first module in the
        # list
        if len(self.tab_bindings) == 1:
            self.tabs.currentIndexChanged.emit()
        elif len(self.tab_bindings) > 1:
            QQmlProperty.write(self.tabs, "currentIndex", "0")

    def _macos_focus_workaround(self) -> None:
        """Set the focus correctly after minimizing Pext on macOS."""
        if platform.system() != 'Darwin' or pyautogui_error:
            return

        hotkey('command', 'tab')

    def _update_active_module(self) -> None:
        """Mark this module as the focused module."""
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        if current_tab < 0:
            return

        Core.set_focused_module_id(current_tab)

    def _bind_context(self) -> None:
        """Bind the context for the module."""
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        if current_tab < 0:
            return

        element = self.tab_bindings[current_tab]

        # Only initialize once, ensure filter is applied
        if element.uiModule.init:
            element.uiModule.vm.search(new_entries=True)
            return

        # Get the header
        header_text = self.tabs.getTab(
            current_tab).findChild(QObject, "headerText")

        # Get the list
        result_list_model = self.tabs.getTab(
            current_tab).findChild(QObject, "resultListModel")

        # Get the info panels
        base_info_panel = self.tabs.getTab(
            current_tab).findChild(QObject, "baseInfoPanel")
        context_info_panel = self.tabs.getTab(
            current_tab).findChild(QObject, "contextInfoPanel")

        # Get the context menu
        context_menu_model = self.tabs.getTab(
            current_tab).findChild(QObject, "contextMenuModel")

        # Enable mouse selection support
        result_list_model.entryClicked.connect(element.uiModule.vm.select)
        result_list_model.selectExplicitNoMinimize.connect(
                    lambda: element.uiModule.vm.select(disable_minimize=True))
        result_list_model.openContextMenu.connect(element.uiModule.vm.show_context)
        result_list_model.openArgumentsInput.connect(element.uiModule.vm.input_args)
        context_menu_model.currentIndexChanged.connect(element.update_context_menu_index)
        context_menu_model.entryClicked.connect(element.uiModule.vm.select)
        context_menu_model.selectExplicitNoMinimize.connect(
                    lambda: element.uiModule.vm.select(disable_minimize=True))
        context_menu_model.openArgumentsInput.connect(element.uiModule.vm.input_args)
        context_menu_model.closeContextMenu.connect(element.uiModule.vm.hide_context)

        # Enable changing sort mode
        result_list_model.sortModeChanged.connect(element.uiModule.vm.next_sort_mode)

        # Enable info pane
        result_list_model.currentIndexChanged.connect(element.uiModule.vm.update_context_info_panel)
        result_list_model.currentIndexChanged.connect(element.update_result_list_index)

        # Bind to the WindowModule
        element.bind_header_text(header_text)
        element.bind_result_list_model(result_list_model)
        element.bind_base_info_panel(base_info_panel)
        element.bind_context_info_panel(context_info_panel)
        element.bind_context_menu_model(context_menu_model)

        # Bind everything to the viewmodel
        element.uiModule.vm.bind_search_string_changed_callback(element.search_string_changed)
        element.uiModule.vm.bind_result_list_changed_callback(element.result_list_changed)
        element.uiModule.vm.bind_result_list_index_changed_callback(element.result_list_index_changed)
        element.uiModule.vm.bind_context_menu_enabled_changed_callback(element.context_menu_enabled_changed)
        element.uiModule.vm.bind_context_menu_index_changed_callback(element.context_menu_index_changed)
        element.uiModule.vm.bind_context_menu_list_changed_callback(element.context_menu_list_changed)
        element.uiModule.vm.bind_context_info_panel_changed_callback(element.context_info_panel_changed)
        element.uiModule.vm.bind_base_info_panel_changed_callback(element.base_info_panel_changed)
        element.uiModule.vm.bind_sort_mode_changed_callback(element.sort_mode_changed)
        element.uiModule.vm.bind_unprocessed_count_changed_callback(element.unprocessed_count_changed)
        element.uiModule.vm.bind_selection_changed_callback(element.selection_changed)
        element.uiModule.vm.bind_header_text_changed_callback(element.header_text_changed)
        element.uiModule.vm.bind_ask_argument_callback(self.ask_argument)
        element.uiModule.vm.bind_close_request_callback(self.close)

        # Done initializing
        element.uiModule.init = True

    def _process_window_state(self, event) -> None:
        if event & Qt.WindowMinimized:
            if Settings.get('minimize_mode') in [MinimizeMode.Tray, MinimizeMode.TrayManualOnly]:
                self.close(manual=True, force_tray=True)

    def _get_current_element(self) -> Optional[WindowModule]:
        current_tab = QQmlProperty.read(self.tabs, "currentIndex")
        try:
            return self.tab_bindings[current_tab]
        except IndexError:
            # No tabs
            return None

    def _go_up(self, to_base=False) -> None:
        element = self._get_current_element()
        if element:
            try:
                if element.uiModule.vm.stopped:
                    self.close(True, False)
                else:
                    element.uiModule.vm.go_up()
            except TypeError:
                pass

    def _go_up_to_base_and_minimize(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                if element.uiModule.vm.stopped:
                    self.close(True, False)
                else:
                    self._go_up(to_base=True)
            except TypeError:
                pass

        self.close(manual=True)

    def open_load_tab(self) -> None:
        """Open the tab to load a new module."""
        # TODO: Support giving the module name
        self.menu_load_module_shortcut.trigger()

    def _open_tab(self, identifier: str, name: str, settings: str) -> None:
        module_settings = {}
        for setting in settings.split(" "):
            try:
                key, value = setting.split("=", 2)
            except ValueError:
                continue

            module_settings[key] = value

        metadata = ModuleManager().get_info(identifier)['metadata']  # type: ignore
        module = {'metadata': metadata, 'settings': module_settings}
        self.module_manager.load(module, None, self)

    def _close_tab(self) -> None:
        if len(self.tab_bindings) > 0:
            tab_id = QQmlProperty.read(self.tabs, "currentIndex")
            self.module_manager.stop(tab_id)
            self.module_manager.unload(tab_id, False, self)

    def _reload_active_module(self) -> None:
        if len(self.tab_bindings) > 0:
            tab_id = QQmlProperty.read(self.tabs, "currentIndex")
            module_data = self.module_manager.reload_step_unload(tab_id, self)
            self.module_manager.reload_step_load(tab_id, module_data, self)

    def _menu_install_module(self, module_url: str, identifier: str, name: str, branch: str) -> None:
        functions = [
            {
                'name': self.module_manager.install,
                'args': (module_url, identifier, name, branch.encode()),
                'kwargs': {'interactive': False, 'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }, {
                'name': InternalCallProcessor.enqueue,
                'args': ("pext:open_load_tab:{}".format(identifier),),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_uninstall_module(self, identifier: str) -> None:
        functions = [
            {
                'name': self.module_manager.uninstall,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_module(self, identifier: str) -> None:
        if not self.module_manager.has_update(identifier):
            return

        for tab in self.tab_bindings:
            if tab.uiModule.metadata['id'] == identifier:
                data = self.module_manager.get_info(identifier)
                self.add_actionable(
                    "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                    Translation.get("actionable_object_update_available_in_use").format(
                        data['metadata']['name']),  # type: ignore
                    Translation.get("actionable_object_update_available_in_use_button"),
                    "pext:update-module-in-use:{}".format(identifier)
                )
                return

        functions = [
            {
                'name': self.module_manager.update,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_modules_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_restart_pext(self, extra_args=None) -> None:
        Core.restart(extra_args)

    def _menu_switch_theme(self, theme_identifier: Optional[str]) -> None:
        Settings.set('theme', theme_identifier)

        self._menu_restart_pext()

    def _menu_switch_profile(self, profile_name: str, new_instance=bool) -> None:
        extra_args = ['--profile={}'.format(profile_name)]
        if not new_instance:
            self._menu_restart_pext(extra_args)
        else:
            args = sys.argv[:]
            args.extend(extra_args)
            args.insert(0, sys.executable)

            Popen(args)

    def _menu_create_profile(self, profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.create_profile,
                'args': (profile_name,),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_rename_profile(self, old_profile_name: str, new_profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.rename_profile,
                'args': (old_profile_name, new_profile_name),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_remove_profile(self, profile_name: str) -> None:
        functions = [
            {
                'name': self.profile_manager.remove_profile,
                'args': (profile_name,),
                'kwargs': {}
            }, {
                'name': self._update_profiles_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_install_theme(self, theme_url: str, identifier: str, name: str, branch: str) -> None:
        functions = [
            {
                'name': self.theme_manager.install,
                'args': (theme_url, identifier, name, branch.encode()),
                'kwargs': {'interactive': False, 'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_uninstall_theme(self, identifier: str) -> None:
        functions = [
            {
                'name': self.theme_manager.uninstall,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_theme(self, identifier: str) -> None:
        functions = [
            {
                'name': self.theme_manager.update,
                'args': (identifier,),
                'kwargs': {'verbose': True}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_update_all_themes(self, verbose=False) -> None:
        functions = [
            {
                'name': self.theme_manager.update_all,
                'args': (),
                'kwargs': {'verbose': False}
            }, {
                'name': self._update_themes_info_qml,
                'args': (),
                'kwargs': {}
            }
        ]
        threading.Thread(target=RunConseq, args=(functions,)).start()  # type: ignore

    def _menu_toggle_turbo_mode(self, enabled: bool) -> None:
        Settings.set('turbo_mode', enabled)
        if enabled:
            for tab in self.tab_bindings:
                tab.uiModule.vm.search(new_entries=True)

    def _menu_change_language(self, lang_code: str) -> None:
        Settings.set('locale', lang_code)
        self._menu_restart_pext()

    def _menu_output_default_clipboard(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.DefaultClipboard)

    def _menu_output_selection_clipboard(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.SelectionClipboard)

    def _menu_output_find_buffer(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_mode', OutputMode.FindBuffer)

    def _menu_output_auto_type(self, enabled: bool) -> None:
        if enabled:
            if platform.system() == 'Darwin' and pyautogui_error:
                Logger.log_critical(None, Translation.get("pyautogui_is_unavailable"), pyautogui_error)
                QQmlProperty.write(self.menu_output_auto_type, "checked", False)
                QQmlProperty.write(self.menu_output_default_clipboard, "checked", True)
                return

            if platform.system() != 'Darwin' and pynput_error:
                Logger.log_critical(None, Translation.get("pynput_is_unavailable"), pynput_error)
                QQmlProperty.write(self.menu_output_auto_type, "checked", False)
                QQmlProperty.write(self.menu_output_default_clipboard, "checked", True)
                return

            Settings.set('output_mode', OutputMode.AutoType)

    def _menu_output_separator_none(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.None_)

    def _menu_output_separator_enter(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.Enter)

    def _menu_output_separator_tab(self, enabled: bool) -> None:
        if enabled:
            Settings.set('output_separator', OutputSeparator.Tab)

    def _menu_minimize_normally(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.Normal)

    def _menu_minimize_to_tray(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.Tray)

    def _menu_minimize_normally_manually(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.NormalManualOnly)

    def _menu_minimize_to_tray_manually(self, enabled: bool) -> None:
        if enabled:
            Settings.set('minimize_mode', MinimizeMode.TrayManualOnly)

    def _menu_enable_global_hotkey_shortcut(self, enabled: bool) -> None:
        if enabled and pynput_error:
            Logger.log_critical(None, Translation.get("pynput_is_unavailable"), pynput_error)
            QQmlProperty.write(self.menu_enable_global_hotkey_shortcut, "checked", False)
            return

        Settings.set('global_hotkey_enabled', enabled)

    def _menu_toggle_tray_icon(self, enabled: bool) -> None:
        Settings.set('tray', enabled)
        try:
            self.tray.show() if enabled else self.tray.hide()  # type: ignore
        except AttributeError:
            pass

    def _menu_install_quick_action_service(self) -> None:
        new_path = os.path.join(ConfigRetriever.get_temp_path(), 'Pext.workflow')
        try:
            rmtree(new_path)
        except IOError:
            pass

        copytree(os.path.join(AppFile.get_path(), 'Pext.workflow'), new_path)
        Popen(['open', new_path])

    def _menu_toggle_update_check(self, enabled: bool) -> None:
        Settings.set('update_check', enabled)
        QQmlProperty.write(self.menu_enable_update_check_shortcut,
                           "checked",
                           Settings.get('update_check'))

        # Check for updates immediately after toggling true
        self._menu_check_updates(verbose=False, manual=False)

    def _menu_toggle_object_update_check(self, enabled: bool) -> None:
        Settings.set('object_update_check', enabled)
        QQmlProperty.write(self.menu_enable_object_update_check_shortcut,
                           "checked",
                           Settings.get('object_update_check'))
        if not enabled:
            self._menu_toggle_object_update_install(False)

    def _menu_toggle_object_update_install(self, enabled: bool) -> None:
        Settings.set('object_update_install', enabled)
        QQmlProperty.write(self.menu_enable_object_update_install_shortcut,
                           "checked",
                           Settings.get('object_update_install'))

    def _search(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element.uiModule.vm.search_string = QQmlProperty.read(self.search_input_model, "text")
                element.uiModule.vm.search(manual=True)
            except TypeError:
                pass

    def _select(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element.uiModule.vm.select()
            except TypeError:
                pass

    def _tab_complete(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element.uiModule.vm.tab_complete()
            except TypeError:
                pass

    def _input_args(self) -> None:
        element = self._get_current_element()
        if element:
            try:
                element.uiModule.vm.input_args()
            except TypeError:
                pass

    def _update_modules_info_qml(self) -> None:
        modules = self.module_manager.list()
        self.context.setContextProperty(
            "modules", modules)
        QQmlProperty.write(
            self.intro_screen, "modulesInstalledCount", len(modules.keys()))

    def _update_themes_info_qml(self) -> None:
        themes = self.theme_manager.list()
        self.context.setContextProperty(
            "themes", themes)

    def _update_profiles_info_qml(self) -> None:
        profiles = self.profile_manager.list_profiles()
        self.context.setContextProperty(
            "profiles", profiles)

    def _menu_check_updates_actually_check(self, verbose=True) -> None:
        if verbose:
            Logger.log(None, Translation.get("checking_for_pext_updates"))

        try:
            new_version = UpdateManager().check_core_update()
        except Exception as e:
            Logger.log_error(None, Translation.get("failed_to_check_for_pext_updates").format(e))
            traceback.print_exc()

            return

        if new_version:
            self.add_actionable(
                "pext_update_available",
                Translation.get("actionable_update_available").format(new_version, UpdateManager().get_core_version()),
                Translation.get("actionable_update_available_button"),
                "https://pext.io/download/")
        else:
            if verbose:
                Logger.log(None, Translation.get("pext_is_already_up_to_date"))

    def _menu_check_updates(self, verbose=True, manual=True) -> None:
        # Set a timer to run this function again in an hour
        if not manual:
            t = threading.Timer(3600, self._menu_check_updates, None, {'verbose': False, 'manual': False})
            t.daemon = True
            t.start()

        # Check if it's been over 24 hours or this is a manual/first check
        last_update_check = Settings.get('last_update_check')

        if manual or last_update_check is None or (time.time() - float(last_update_check) > 86400):
            if USE_INTERNAL_UPDATER:
                if manual or Settings.get('update_check'):
                    threading.Thread(target=self._menu_check_updates_actually_check, args=(verbose,)).start()

            if manual or Settings.get('object_update_check'):
                if Settings.get('object_update_install'):
                    for module_id, data in self.module_manager.list().items():
                        self._menu_update_module(module_id)

                    self._menu_update_all_themes(verbose)
                else:
                    for module_id, data in self.module_manager.list().items():
                        if self.module_manager.has_update(module_id):
                            self.add_actionable(
                                "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                                Translation.get("actionable_object_update_available").format(
                                    data['metadata']['name']),  # type: ignore
                                Translation.get("actionable_object_update_available_button"),
                                "pext:update-module-in-use:{}".format(module_id)
                            )
                    for theme_id, data in self.theme_manager.list().items():
                        if self.theme_manager.has_update(theme_id):
                            self.add_actionable(
                                "object_update_available_in_use_{}".format(data['metadata']['id']),  # type: ignore
                                Translation.get("actionable_object_update_available").format(
                                    data['metadata']['name']),  # type: ignore
                                Translation.get("actionable_object_update_available_button"),
                                "pext:update-theme:{}".format(module_id)
                            )

            Settings.set('last_update_check', time.time())

    def _show_homepage(self) -> None:
        webbrowser.open('https://pext.io/')

    def _remove_actionable(self, index: int) -> None:
        self.actionables.pop(index)
        QQmlProperty.write(self.window, 'actionables', self.actionables)

    def add_module(self, uiModule: UiModule, index=None) -> bool:
        """Add a module to the UI."""
        # Prepare necessary lists
        result_list_model_list = QStringListModel()
        context_menu_model_list = QStringListModel()
        context_menu_model_list_full = QStringListModel()

        # Prepare context
        module_context = QQmlContext(self.context)
        module_context.setContextProperty(
            "sortMode", uiModule.vm.sort_mode)
        module_context.setContextProperty(
            "resultListModel", result_list_model_list)
        module_context.setContextProperty(
            "resultListModelNormalEntries", 0)
        module_context.setContextProperty(
            "resultListModelCommandEntries", 0)
        module_context.setContextProperty(
            "resultListModelHasEntries", False)
        module_context.setContextProperty(
            "resultListModelCommandMode", False)
        module_context.setContextProperty(
            "resultListModelTree", [])
        module_context.setContextProperty(
            "unprocessedCount", 0)
        module_context.setContextProperty(
            "contextMenuModel", context_menu_model_list)
        module_context.setContextProperty(
            "contextMenuModelFull", context_menu_model_list_full)
        module_context.setContextProperty(
            "contextMenuModelEntrySpecificCount", 0)
        module_context.setContextProperty(
            "contextMenuEnabled", False)
        module_context.setContextProperty(
            "searchInputFieldEmpty", True)

        # Create tab
        tab_data = QQmlComponent(self.engine)
        tab_data.loadUrl(
            QUrl.fromLocalFile(os.path.join(AppFile.get_path(), 'qml', 'ModuleData.qml')))
        self.engine.setContextForObject(tab_data, module_context)

        # Create module
        window_module = WindowModule(
            self,
            uiModule,
            module_context,
            tab_data,
            result_list_model_list,
            context_menu_model_list,
            context_menu_model_list_full)

        # Store tab/viewModel combination
        # tabData is not used but stored to prevent segfaults caused by
        # Python garbage collecting it
        if index is not None:
            self.tab_bindings.insert(index, window_module)
        else:
            self.tab_bindings.append(window_module)

        # Add/replace tab
        if index is not None:
            self.tabs.insertTab(index, uiModule.metadata['name'], tab_data)
            self.tabs.removeRequest.emit(index + 1)
            del self.tab_bindings[index + 1]
        else:
            self.tabs.addTab(uiModule.metadata['name'], tab_data)

        # Open tab to trigger loading
        if index is not None:
            QQmlProperty.write(
                self.tabs, "currentIndex", index)
        else:
            QQmlProperty.write(
                self.tabs, "currentIndex", QQmlProperty.read(self.tabs, "count") - 1)

        # Save active modules
        ProfileManager().save_modules(
            Settings.get('profile'),
            [windowModule.uiModule for windowModule in self.tab_bindings])

        # First module? Enforce load
        if len(self.tab_bindings) == 1:
            self.tabs.currentIndexChanged.emit()

        return True

    def remove_module(self, tab_id: int, for_reload=False) -> None:
        """Remove a module from the UI."""
        if for_reload:
            # We'll reload the module very soon
            # Don't delete it yet
            return

        if QQmlProperty.read(self.tabs, "currentIndex") == tab_id:
            tab_count = QQmlProperty.read(self.tabs, "count")
            if tab_count == 1:
                QQmlProperty.write(self.tabs, "currentIndex", "-1")
            elif tab_id + 1 < tab_count:
                QQmlProperty.write(self.tabs, "currentIndex", tab_id + 1)
            else:
                QQmlProperty.write(self.tabs, "currentIndex", "0")

        self.tabs.removeRequest.emit(tab_id)
        del self.tab_bindings[tab_id]

        # Ensure a proper refresh on the UI side
        self.tabs.currentIndexChanged.emit()

    def disable_module(self, tab_id: int, reason: int) -> None:
        """Disable a module by tab ID.

        Valid reasons:
        1: Crash
        2: Update
        """
        self.tabs.disableRequest.emit(tab_id, reason)

    def update_state(self, tab_id: int, state: str) -> None:
        """Update a module's state by tab ID.

        This adds an entry to display in the module's disabled screen.

        Used for showing installation, update progress or module crashes.
        """
        self.tabs.updateStateRequest.emit(tab_id, state)

    def add_actionable(self, identifier: str, text: str, button_text=None, button_url=None, urgency="medium") -> None:
        """Add an action to show in the UI."""
        new_actionable = {
            'identifier': identifier,
            'text': text,
            'buttonText': button_text if button_text else "",
            'buttonUrl': button_url if button_url else "",
            'urgency': urgency
        }

        for index, actionable in enumerate(self.actionables):
            if actionable['identifier'] == identifier:
                self.actionables[index] = new_actionable
                break
        else:
            self.actionables.insert(0, new_actionable)

        QQmlProperty.write(self.window, 'actionables', self.actionables)

    def bind_tray(self, tray: 'Tray') -> None:
        """Bind the tray to the window."""
        self.tray = tray

        if Settings.get('tray'):
            tray.show()

    def ask_argument(self, entry: str, callback: Callable) -> None:
        """Open the ask argument dialog and call the callback when the user has reacted to it."""
        # Disconnect possibly existing handler
        try:
            self.args_request.commandArgsRequestAccepted.disconnect()
        except TypeError:
            pass

        self.args_request.commandArgsRequestAccepted.connect(
            lambda args: callback(args))

        self.args_request.showCommandArgsDialog.emit(entry)

    def ask_question(self, module_name: str, question: str, identifier: Optional[int], callback: Callable) -> None:
        """Open the ask question dialog and call the callback when the user has reacted to it."""
        # Disconnect possibly existing handlers
        try:
            self.question_dialog.questionAccepted.disconnect()
        except TypeError:
            pass
        try:
            self.question_dialog.questionRejected.disconnect()
        except TypeError:
            pass

        if len(signature(callback).parameters) == 2:
            self.question_dialog.questionAccepted.connect(partial(
                lambda arg: callback(True, arg),
                arg=(identifier)))
            self.question_dialog.questionRejected.connect(partial(
                lambda arg: callback(False, arg),
                arg=(identifier)))
        else:
            self.question_dialog.questionAccepted.connect(
                lambda: callback(True))
            self.question_dialog.questionRejected.connect(
                lambda: callback(False))

        self.question_dialog.showQuestionDialog.emit(module_name, question)

    def ask_choice(self, module_name: str, question: str, choices: List[str], identifier: Optional[int],
                   callback: Callable) -> None:
        """Open the ask choice dialog and call the callback when the user has reacted to it."""
        # Disconnect possibly existing handlers
        try:
            self.choice_dialog.choiceAccepted.disconnect()
        except TypeError:
            pass
        try:
            self.choice_dialog.choiceRejected.disconnect()
        except TypeError:
            pass

        if len(signature(callback).parameters) == 2:
            self.choice_dialog.choiceAccepted.connect(partial(
                lambda userinput, arg: callback(userinput, arg),
                arg=(identifier)))
            self.choice_dialog.choiceRejected.connect(partial(
                lambda arg: callback(None, arg),
                arg=(identifier)))
        else:
            self.choice_dialog.choiceAccepted.connect(
                lambda userinput: callback(userinput))
            self.choice_dialog.choiceRejected.connect(
                lambda: callback(None))

        self.choice_dialog.showChoiceDialog.emit(module_name, question, choices)

    def ask_input(self, module_name: str, question: str, prefill: str, password: bool, multiline: bool,
                  identifier: Optional[int], callback: Callable) -> None:
        """Open the ask input dialog and call the callback when the user has reacted to it."""
        try:
            self.input_request.inputRequestAccepted.disconnect()
        except TypeError:
            pass
        try:
            self.input_request.inputRequestRejected.disconnect()
        except TypeError:
            pass

        if len(signature(callback).parameters) == 2:
            self.input_request.inputRequestAccepted.connect(partial(
                lambda userinput, arg: callback(userinput, arg),
                arg=(identifier)))
            self.input_request.inputRequestRejected.connect(partial(
                lambda arg: callback(None, arg),
                arg=(identifier)))
        else:
            self.input_request.inputRequestAccepted.connect(
                lambda userinput: callback(userinput))
            self.input_request.inputRequestRejected.connect(
                lambda: callback(None))

        self.input_request.inputRequest.emit(module_name, question, password, multiline, prefill)

    def set_status_text(self, text: str) -> None:
        """Update the status text in the bottom left corner."""
        QQmlProperty.write(self.status_text, "text", text)

    def close(self, manual=False, force_tray=False) -> None:
        """Close the window."""
        if self.app.platformName() in ['webgl', 'vnc']:
            return

        if force_tray:
            if self.tray:
                self.tray.show()

            self.window.hide()
        else:
            if (not manual
                    and Settings.get('minimize_mode') in [MinimizeMode.NormalManualOnly, MinimizeMode.TrayManualOnly]):
                return

            if Settings.get('minimize_mode') in [MinimizeMode.Normal, MinimizeMode.NormalManualOnly]:
                self.window.showMinimized()
            else:
                self.window.hide()

        self._macos_focus_workaround()

        if self.output_queue:
            output_mode = Settings.get('output_mode')
            if output_mode == OutputMode.AutoType:
                time.sleep(0.5)
                keyboard_device = keyboard.Controller()

                while True:
                    try:
                        output = self.output_queue.pop(0)
                    except IndexError:
                        Logger.log(None, Translation.get("queued_data_typed"))
                        break

                    if platform.system() == "Darwin":
                        # https://github.com/moses-palmer/pynput/issues/83#issuecomment-410264758
                        typewrite(output)
                    else:
                        keyboard_device.type(output)

                    if self.output_queue:
                        separator_key = Settings.get('output_separator')
                        if separator_key == OutputSeparator.None_:
                            continue

                        if platform.system() == "Darwin":
                            if separator_key == OutputSeparator.Tab:
                                hotkey('tab')
                            elif separator_key == OutputSeparator.Enter:
                                hotkey('return')
                        else:
                            if separator_key == OutputSeparator.Tab:
                                key = keyboard.Key.tab
                            elif separator_key == OutputSeparator.Enter:
                                key = keyboard.Key.enter

                            keyboard_device.press(key)
                            keyboard_device.release(key)
            else:
                if output_mode == OutputMode.SelectionClipboard:
                    mode = QClipboard.Selection
                elif output_mode == OutputMode.FindBuffer:
                    mode = QClipboard.FindBuffer
                else:
                    mode = QClipboard.Clipboard

                separator_key = Settings.get('output_separator')
                if separator_key == OutputSeparator.Tab:
                    join_string = "\t"
                elif separator_key == OutputSeparator.Enter:
                    join_string = os.linesep
                else:
                    join_string = ""

                self.app.clipboard().setText(str(join_string.join(self.output_queue)), mode)

                Logger.log(None, Translation.get("data_copied_to_clipboard"))

                self.output_queue = []

    def show(self) -> None:
        """Show the window."""
        if self.tray:
            if Settings.get('tray'):
                self.tray.show()
            else:
                self.tray.hide()

        if self.window.windowState() == Qt.WindowMinimized:
            self.window.showNormal()
        else:
            self.window.show()

        self.window.raise_()

    def switch_tab(self, tab_id) -> None:
        """Switch the active tab."""
        QQmlProperty.write(self.tabs, "currentIndex", tab_id)

    def toggle_visibility(self, force_tray=False) -> None:
        """Toggle window visibility."""
        if self.window.windowState() == Qt.WindowMinimized or not self.window.isVisible():
            self.show()
        else:
            self.close(force_tray=force_tray)

    def quit(self) -> None:
        """Quit."""
        geometry = self.window.geometry()
        Settings.set('_window_geometry',
                     "{};{};{};{}".format(geometry.x(), geometry.y(), geometry.width(), geometry.height()))
        sys.exit(0)


class Tray():
    """Handle the system tray."""

    def __init__(self, window: Window, app_icon: QIcon) -> None:
        """Initialize the system tray."""
        self.window = window

        self.tray = QSystemTrayIcon(app_icon)
        self.tray.activated.connect(self.icon_clicked)  # type: ignore
        self.tray.setToolTip(QQmlProperty.read(self.window.window, "title"))

        self.window.tabs.currentIndexChanged.connect(self._update_context_menu)
        self._update_context_menu()

    def _update_context_menu(self) -> None:
        """Update the context menu to list the loaded modules."""
        tray_menu = QMenu()
        tray_menu_item = QAction(QQmlProperty.read(self.window.window, "title"), tray_menu)
        tray_menu_item.triggered.connect(self.window.show)  # type: ignore
        tray_menu.addAction(tray_menu_item)
        if len(self.window.tab_bindings) > 0:
            tray_menu.addSeparator()

        for tab_id, tab in enumerate(self.window.tab_bindings):
            tray_menu_item = QAction(tab.uiModule.metadata['name'], tray_menu)
            tray_menu_item.triggered.connect(partial(  # type: ignore
                lambda tab_id: [self.window.switch_tab(tab_id), self.window.show()], tab_id=tab_id))  # type: ignore
            tray_menu.addAction(tray_menu_item)

        self.tray.setContextMenu(tray_menu)

    def icon_clicked(self, reason: int) -> None:
        """Toggle window visibility on left click."""
        if reason == 3 and platform.system() != "Darwin":
            self.window.toggle_visibility(force_tray=True)

    def show(self) -> None:
        """Show the tray icon."""
        self.tray.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        self.tray.hide()


class HotkeyHandler():
    """Handles global hotkey presses."""

    def __init__(self, main_loop_queue: Queue, window: 'Window') -> None:
        """Initialize the global hotkey handler."""
        self.window = window
        self.modifiers = set()  # type: Set[Union[keyboard.Key, keyboard.KeyCode]]
        self.backtick = keyboard.KeyCode(char='`')
        self.main_loop_queue = main_loop_queue

        self.modifier_keys = [
            keyboard.Key.ctrl,
            keyboard.Key.shift,
            keyboard.Key.alt,
            keyboard.Key.cmd
        ]

        if not pynput_error:
            listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
            listener.start()

    def on_press(self, key) -> bool:
        """Track pressed keys and show window when all keys for the global hotkey are pressed."""
        if key is None:
            return True

        if key in self.modifier_keys:
            self.modifiers.add(key)
        elif (key == self.backtick and
              len(self.modifiers) == 1 and
              keyboard.Key.ctrl in self.modifiers and
              Settings.get('global_hotkey_enabled')):
            self.main_loop_queue.put(self.window.show)

        return True

    def on_release(self, key) -> bool:
        """Remove key from pressed keys list on release."""
        try:
            self.modifiers.remove(key)
        except KeyError:
            pass

        return True


class SignalHandler():
    """Handle UNIX signals."""

    def __init__(self, window: 'Window') -> None:
        """Initialize SignalHandler."""
        self.window = window

    def handle(self, signum: int, frame) -> None:
        """When an UNIX signal gets received, show the window."""
        self.window.show()
