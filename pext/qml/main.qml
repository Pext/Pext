/*
    Copyright (c) 2015 - 2019 Sylvia van Os <sylvia@hackerchick.me>

    This file is part of Pext.

    Pext is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

import QtQuick 2.13
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0
import QtQuick.Extras 1.0

ApplicationWindow {
    id: applicationWindow
    title: currentProfile == defaultProfile ? qsTr("Pext") : qsTr("Pext (%1)").arg(currentProfile)
    property bool internalUpdaterEnabled: USE_INTERNAL_UPDATER
    property string version: applicationVersion
    property string platform: systemPlatform
    property int margin: 10
    minimumWidth: FORCE_FULLSCREEN ? Screen.width : 800
    minimumHeight: FORCE_FULLSCREEN ? Screen.height : 640
    width: FORCE_FULLSCREEN ? Screen.width : 800
    height: FORCE_FULLSCREEN ? Screen.height : 640

    property var actionables: []
    signal internalCall(string url)

    flags: Qt.Window

    signal confirmedClose()

    onClosing: {
        close.accepted = false;
        var confirmQuitDialog = Qt.createComponent("ConfirmQuitDialog.qml");
        confirmQuitDialog.createObject(applicationWindow,
            {"confirmedClose": confirmedClose,
             "platform": platform});
    }

    SystemPalette { id: palette; colorGroup: SystemPalette.Active }

    Item {
        objectName: "inputRequests"

        signal inputRequest(string moduleName, string description, bool isPassword, bool isMultiline, string prefill)
        signal inputRequestAccepted(string userInput)
        signal inputRequestRejected()

        onInputRequest: {
            var inputRequestDialog = Qt.createComponent("InputRequestDialog.qml");
            inputRequestDialog.createObject(applicationWindow,
                {"moduleName": moduleName,
                 "description": description,
                 "isPassword": isPassword,
                 "isMultiline": isMultiline,
                 "prefill": prefill,
                 "requestAccepted": inputRequestAccepted,
                 "requestRejected": inputRequestRejected});
        }
    }

    Item {
        objectName: "choiceDialog"

        signal showChoiceDialog(string moduleName, string question, var choices)
        signal choiceAccepted(string choice)
        signal choiceRejected()

        onShowChoiceDialog: {
            var choiceDialog = Qt.createComponent("ChoiceDialog.qml");
            choiceDialog.createObject(applicationWindow,
                {"moduleName": moduleName,
                 "question": question,
                 "choices": choices,
                 "accepted": choiceAccepted,
                 "rejected": choiceRejected});
        }
    }

    Item {
        objectName: "questionDialog"

        signal showQuestionDialog(string moduleName, string question)
        signal questionAccepted()
        signal questionRejected()

        onShowQuestionDialog: {
            var questionDialog = Qt.createComponent("QuestionDialog.qml");
            questionDialog.createObject(applicationWindow,
                {"moduleName": moduleName,
                 "question": question,
                 "accepted": questionAccepted,
                 "rejected": questionRejected});
        }
    }

    Item {
        objectName: "commandArgsDialog"

        signal showCommandArgsDialog(string command)
        signal commandArgsRequestAccepted(string args)

        onShowCommandArgsDialog: {
            var commandArgsDialog = Qt.createComponent("CommandArgsDialog.qml");
            commandArgsDialog.createObject(applicationWindow,
                 {"command": command,
                  "requestAccepted": commandArgsRequestAccepted});
        }
    }

    Item {
        objectName: "errorDialog"

        signal showErrorDialog(string moduleName, string message, string detailedMessage)

        onShowErrorDialog: {
            var errorDialog = Qt.createComponent("CriticalErrorDialog.qml");
            errorDialog.createObject(applicationWindow,
              {"moduleName": moduleName,
               "message": message,
               "detailedMessage": detailedMessage});
        }
    }

    function getActiveList() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        if (tab.item.children[0].children[0].visible) {
            return tab.item.children[0].children[0].contentItem;
        } else {
            return tab.item.children[0].children[2].contentItem;
        }
    }

    function isContextMenuVisible() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        return tab.item.children[0].children[0].visible;
    }

    function openContextMenu() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        tab.item.children[0].children[2].contentItem.openContextMenu();
    }

    function selectExplicitNoMinimize() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        tab.item.children[0].children[2].contentItem.selectExplicitNoMinimize();
    }

    function openArgumentsInput() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        tab.item.children[0].children[2].contentItem.openArgumentsInput();
    }

    function moveUp() {
        getActiveList().decrementCurrentIndex();
    }

    function moveDown() {
        getActiveList().incrementCurrentIndex();
    }

    function pageUp() {
        var listView = getActiveList();

        var newIndex = listView.currentIndex - (listView.height / listView.currentItem.height) + 1;

        if (newIndex < 0)
            listView.currentIndex = 0;
        else
            listView.currentIndex = newIndex;

        listView.positionViewAtIndex(listView.currentIndex, ListView.Beginning);
    }

    function pageDown() {
        var listView = getActiveList();

        var newIndex = listView.currentIndex + (listView.height / listView.currentItem.height);
        var maxIndex = listView.count - 1;

        if (newIndex > maxIndex)
            listView.currentIndex = maxIndex;
        else
            listView.currentIndex = newIndex;

        listView.positionViewAtIndex(listView.currentIndex, ListView.Beginning);
    }

    function nextTab() {
        if (tabs.currentIndex < tabs.count - 1)
            tabs.currentIndex += 1;
        else
            tabs.currentIndex = 0;
    }

    function prevTab() {
        if (tabs.currentIndex > 0)
            tabs.currentIndex -= 1;
        else
            tabs.currentIndex = tabs.count - 1;
    }

    function switchTab(id) {
        if (tabs.count - 1 >= id)
            tabs.currentIndex = id;
    }

    Shortcut {
        id: escapeShortcut
        objectName: "escapeShortcut"
        sequence: "Escape"
    }

    Shortcut {
        id: shiftEscapeShortcut
        objectName: "shiftEscapeShortcut"
        sequence: "Shift+Escape"
    }

    Shortcut {
        id: tabShortcut
        objectName: "tabShortcut"
        sequence: "Tab"
    }

    Shortcut {
        id: contextMenuShortcut
        sequence: "Ctrl+."
        onActivated: openContextMenu();
    }

    Shortcut {
        id: enterShortcut
        enabled: false
        sequence: "Return"
    }

    Shortcut {
        id: noMinimizeShortcut
        sequence: "Shift+Return"
        onActivated: selectExplicitNoMinimize()
    }

    Shortcut {
        id: argsShortcut
        objectName: "argsShortcut"
        sequence: "Ctrl+Return"
    }

    Shortcut {
        sequence: StandardKey.MoveToPreviousLine
        onActivated: moveUp();
    }

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: moveUp();
    }

    Shortcut {
        sequence: StandardKey.MoveToNextLine
        onActivated: moveDown();
    }

    Shortcut {
        sequence: "Ctrl+J"
        onActivated: moveDown();
    }

    Shortcut {
        sequence: StandardKey.MoveToPreviousPage
        onActivated: pageUp()
    }

    Shortcut {
        sequence: "Ctrl+B"
        onActivated: pageUp()
    }

    Shortcut {
        sequence: StandardKey.MoveToNextPage
        onActivated: pageDown()
    }

    Shortcut {
        sequence: "Ctrl+F"
        onActivated: pageDown()
    }

    // Actual trigger is in menu due to https://bugreports.qt.io/browse/QTBUG-8596?focusedCommentId=215198&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-215198
    Shortcut {
        id: nextTabShortcut
        sequence: platform == 'Darwin' ? "Meta+Tab" : "Ctrl+Tab" // QTBUG-15746 and QTBUG-7001
        enabled: false
    }

    // Actual trigger is in menu due to https://bugreports.qt.io/browse/QTBUG-8596?focusedCommentId=215198&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-215198
    Shortcut {
        id: previousTabShortcut
        sequence: platform == 'Darwin' ? "Meta+Shift+Tab" : "Ctrl+Shift+Tab" // QTBUG-15746 and QTBUG-7001
        enabled: false
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+1" : "Ctrl+1"
        onActivated: switchTab(0)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+2" : "Ctrl+2"
        onActivated: switchTab(1)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+3" : "Ctrl+3"
        onActivated: switchTab(2)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+4" : "Ctrl+4"
        onActivated: switchTab(3)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+5" : "Ctrl+5"
        onActivated: switchTab(4)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+6" : "Ctrl+6"
        onActivated: switchTab(5)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+7" : "Ctrl+7"
        onActivated: switchTab(6)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+8" : "Ctrl+8"
        onActivated: switchTab(7)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+9" : "Ctrl+9"
        onActivated: switchTab(8)
    }

    Shortcut {
        sequence: platform == 'Linux' ? "Alt+0" : "Ctrl+0"
        onActivated: switchTab(9)
    }

    Shortcut {
        id: activateActionableShortcut
        sequence: "Ctrl+Y"
        onActivated: {
            if (actionables.length > 0) {
                actionableRepeater.activateActionable(0);
            }
        }
    }

    Shortcut {
        id: dismissActionableShortcut
        sequence: "Ctrl+N"
        onActivated: {
            if (actionables.length > 0) {
                actionableRepeater.removeActionable(0);
            }
        }
    }

    Shortcut {
        id: changeSortModeShortcut
        sequence: "Ctrl+S"
        onActivated: statusSortMode.sortModeChanged()
    }

    menuBar: MenuBar {
        Menu {
            title: qsTr("&Pext")

            MenuItem {
                objectName: "menuQuit"
                text: platform == 'Darwin' ? "Quit" : qsTr("Quit")
                shortcut: StandardKey.Quit
            }
        }

        Menu {
            title: qsTr("&Module")

            // Has to be in menu for macOS due to https://bugreports.qt.io/browse/QTBUG-8596?focusedCommentId=215198&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-215198
            MenuItem {
                text: qsTr("Switch to next loaded module")
                shortcut: platform == 'Darwin' ? "Meta+Tab" : "Ctrl+Tab" // QTBUG-15746 and QTBUG-7001
                onTriggered: nextTab()
                enabled: tabs.count > 1
            }

            // Has to be in menu for macOS due to https://bugreports.qt.io/browse/QTBUG-8596?focusedCommentId=215198&page=com.atlassian.jira.plugin.system.issuetabpanels%3Acomment-tabpanel#comment-215198
            MenuItem {
                text: qsTr("Switch to previous loaded module")
                shortcut: platform == 'Darwin' ? "Meta+Shift+Tab" : "Ctrl+Shift+Tab" // QTBUG-15746 and QTBUG-7001
                onTriggered: prevTab()
                enabled: tabs.count > 1
            }

            MenuSeparator { }

            MenuItem {
                id: menuReloadActiveModule
                objectName: "menuReloadActiveModule"
                text: qsTr("Reload active module")
                shortcut: StandardKey.Refresh
                enabled: tabs.count
            }

            MenuItem {
                id: menuCloseActiveModule
                objectName: "menuCloseActiveModule"
                text: qsTr("Close active module")
                shortcut: StandardKey.Close
                enabled: tabs.count
            }

            MenuSeparator { }

            MenuItem {
                id: menuLoadModule
                objectName: "menuLoadModule"

                signal loadModuleRequest(string identifier, string name, string settings)

                text: qsTr("Load module")

                shortcut: StandardKey.AddTab

                onTriggered: {
                    if (Object.keys(modules).length == 0) {
                        menuInstallModuleFromList.trigger();
                    } else {
                        var loadModuleDialog = Qt.createComponent("LoadModuleDialog.qml");
                        loadModuleDialog.createObject(applicationWindow,
                            {"modules": modules,
                             "loadRequest": loadModuleRequest,
                             "modulesPath": modulesPath,
                             "menuInstallModule": menuInstallModuleFromList});
                    }
                }
            }

            MenuItem {
                id: menuManageModules
                objectName: "menuManageModules"
                text: qsTr("Manage modules")

                signal updateModuleRequest(string identifier)
                signal uninstallModuleRequest(string identifier)

                onTriggered: {
                    if (Object.keys(modules).length == 0) {
                        var noModulesInstalledDialog = Qt.createComponent("NoModulesInstalledDialog.qml");
                        noModulesInstalledDialog.createObject(applicationWindow);
                    } else {
                        var manageDialog = Qt.createComponent("ManageDialog.qml");
                        manageDialog.createObject(applicationWindow,
                            {"type": "modules",
                             "manageableObjects": modules,
                             "updateRequest": updateModuleRequest,
                             "uninstallRequest": uninstallModuleRequest});
                    }
                }
            }

            Menu {
                id: menuInstallModule
                objectName: "menuInstallModule"
                title: qsTr("Install module")

                signal installModuleRequest(string url, string identifier, string name)

                MenuItem {
                    id: menuInstallModuleFromList
                    text: qsTr("From online module list")

                    property var repositories:
                        [{
                          "name": "Pext team",
                          "url": "https://pext.io/modules_v2.json"
                        }, {
                          "name": "Other developers",
                          "url": "https://pext.io/third_party_modules_v2.json"
                        }]

                    onTriggered: {
                        var installModuleFromRepositoryDialog = Qt.createComponent("InstallFromRepositoryDialog.qml");
                        installModuleFromRepositoryDialog.createObject(applicationWindow,
                            {"installedObjects": modules,
                             "installRequest": menuInstallModule.installModuleRequest,
                             "repositories": repositories,
                             "type": "modules",
                             "currentLocaleCode": currentLocaleCode})
                    }
                }

                MenuItem {
                    text: qsTr("From URL")

                    onTriggered: {
                        var installModuleFromURLDialog = Qt.createComponent("InstallModuleFromURLDialog.qml");
                        installModuleFromURLDialog.createObject(applicationWindow,
                            {"installRequest": menuInstallModule.installModuleRequest});
                    }
                }
            }
        }

        Menu {
            title: qsTr("&Theme")

            MenuItem {
                id: menuLoadTheme
                objectName: "menuLoadTheme"

                signal loadThemeRequest(string identifier)

                text: qsTr("Switch theme")

                onTriggered: {
                    if (Object.keys(themes).length == 0) {
                        menuInstallThemeFromList.trigger();
                    } else {
                        var loadThemeDialog = Qt.createComponent("LoadThemeDialog.qml");
                        loadThemeDialog.createObject(applicationWindow,
                            {"currentTheme": currentTheme,
                             "themes": themes,
                             "loadRequest": loadThemeRequest,
                             "themesPath": themesPath,
                             "menuInstallTheme": menuInstallThemeFromList});
                    }
                }
            }

            MenuItem {
                id: menuManageThemes
                objectName: "menuManageThemes"
                text: qsTr("Manage themes")

                signal updateThemeRequest(string identifier)
                signal uninstallThemeRequest(string identifier)

                onTriggered: {
                    if (Object.keys(themes).length == 0) {
                        var noThemesInstalledDialog = Qt.createComponent("NoThemesInstalledDialog.qml");
                        noThemesInstalledDialog.createObject(applicationWindow);
                    } else {
                        var manageDialog = Qt.createComponent("ManageDialog.qml");
                        manageDialog.createObject(applicationWindow,
                            {"type": "themes",
                             "manageableObjects": themes,
                             "updateRequest": updateThemeRequest,
                             "uninstallRequest": uninstallThemeRequest});
                    }
                }
            }

            Menu {
                id: menuInstallTheme
                objectName: "menuInstallTheme"
                title: qsTr("Install theme")

                signal installThemeRequest(string url, string identifier, string name)

                MenuItem {
                    id: menuInstallThemeFromList
                    text: qsTr("From online theme list")

                    property var repositories:
                        [{
                          "name": "Pext team",
                          "url": "https://pext.io/themes_v2.json"
                        }, {
                          "name": "Other developers",
                          "url": "https://pext.io/third_party_themes_v2.json"
                        }]

                    onTriggered: {
                        var installThemeFromRepositoryDialog = Qt.createComponent("InstallFromRepositoryDialog.qml");
                        installThemeFromRepositoryDialog.createObject(applicationWindow,
                            {"installedObjects": themes,
                             "installRequest": menuInstallTheme.installThemeRequest,
                             "repositories": repositories,
                             "type": "themes",
                             "currentLocaleCode": currentLocaleCode})
                    }
                }

                MenuItem {
                    text: qsTr("From URL")

                    onTriggered: {
                        var installThemeFromURLDialog = Qt.createComponent("InstallThemeFromURLDialog.qml");
                        installThemeFromURLDialog.createObject(applicationWindow,
                            {"installRequest": menuInstallTheme.installThemeRequest});
                    }
                }
            }
        }

        Menu {
            title: qsTr("P&rofile")

            MenuItem {
                objectName: "menuLoadProfile"
                text: qsTr("Switch profile")

                signal loadProfileRequest(string name, bool newInstance)

                onTriggered: {
                    if (profiles.length < 1) {
                        var onlyOneProfileDialog = Qt.createComponent("OnlyOneProfileDialog.qml");
                        onlyOneProfileDialog.createObject(applicationWindow);
                    } else {
                        var loadProfileDialog = Qt.createComponent("LoadProfileDialog.qml");
                        loadProfileDialog.createObject(applicationWindow,
                            {"currentProfile": currentProfile,
                             "profiles": profiles.sort(),
                             "loadRequest": loadProfileRequest});
                    }
                }
            }

            MenuItem {
                objectName: "menuManageProfiles"
                text: qsTr("Manage profiles")

                signal createProfileRequest(string name)
                signal renameProfileRequest(string oldName, string newName)
                signal removeProfileRequest(string name)

                onTriggered: {
                    var manageProfilesDialog = Qt.createComponent("ManageProfilesDialog.qml");
                    manageProfilesDialog.createObject(applicationWindow,
                        {"profiles": profiles.sort(),
                         "createRequest": createProfileRequest,
                         "renameRequest": renameProfileRequest,
                         "removeRequest": removeProfileRequest});
                }
            }
        }

        Menu {
            title: platform == 'Darwin' ? "Settings" : qsTr("&Settings")

            MenuItem {
                objectName: "menuTurboMode"
                text: qsTr("Turbo Mode")
                checkable: true
            }

            Menu {
                id: menuChangeLanguage
                objectName: "menuChangeLanguage"

                title: qsTr("Language")

                signal changeLanguage(string langcode)

                ExclusiveGroup {
                    id: menuLanguageGroup
                    objectName: "menuLanguageGroup"
                }

                MenuItem {
                    text: qsTr("System locale")
                    checked: currentLocale === null
                    checkable: true
                    exclusiveGroup: menuLanguageGroup
                    onTriggered: menuChangeLanguage.changeLanguage(null)
                }

                MenuSeparator {}

                Instantiator {
                    model: Object.keys(locales).sort(function (a, b) { return a.toLowerCase().localeCompare(b.toLowerCase()); });
                    onObjectAdded: menuChangeLanguage.insertItem(index, object)
                    onObjectRemoved: menuChangeLanguage.removeItem(object)
                    delegate: MenuItem {
                        text: modelData
                        checked: currentLocale !== null && currentLocale.nativeLanguageName == modelData
                        checkable: true
                        exclusiveGroup: menuLanguageGroup
                        onTriggered: menuChangeLanguage.changeLanguage(locales[modelData])
                    }
                }
            }

            Menu {
                title: qsTr("Output style")

                ExclusiveGroup {
                    id: menuOutputGroup
                    objectName: "menuOutputGroup"
                }

                MenuItem {
                    objectName: "menuOutputDefaultClipboard"
                    text: qsTr("Copy to default clipboard")
                    checkable: true
                    exclusiveGroup: menuOutputGroup
                }

                MenuItem {
                    visible: platform == 'Linux'
                    objectName: "menuOutputSelectionClipboard"
                    text: qsTr("Copy to selection clipboard (X11)")
                    checkable: true
                    exclusiveGroup: menuOutputGroup
                }

                MenuItem {
                    visible: platform == 'Darwin'
                    objectName: "menuOutputFindBuffer"
                    text: qsTr("Copy to find buffer (macOS)")
                    checkable: true
                    exclusiveGroup: menuOutputGroup
                }

                MenuItem {
                    objectName: "menuOutputAutoType"
                    text: qsTr("Type automatically")
                    checkable: true
                    exclusiveGroup: menuOutputGroup
                }

                Menu {
                    title: qsTr("Separator between output queue entries")

                    ExclusiveGroup {
                        id: menuOutputSeparatorGroup
                        objectName: "menuOutputSeparatorGroup"
                    }
    
                    MenuItem {
                        objectName: "menuOutputSeparatorNone"
                        text: qsTr("Nothing")
                        checkable: true
                        exclusiveGroup: menuOutputSeparatorGroup
                    }

                    MenuItem {
                        objectName: "menuOutputSeparatorEnter"
                        text: enterShortcut.nativeText
                        checkable: true
                        exclusiveGroup: menuOutputSeparatorGroup
                    }

                    MenuItem {
                        objectName: "menuOutputSeparatorTab"
                        text: tabShortcut.nativeText
                        checkable: true
                        exclusiveGroup: menuOutputSeparatorGroup
                    }
                }
            }

            Menu {
                title: qsTr("Minimizing behaviour")

                ExclusiveGroup {
                    id: menuMinimizeGroup
                    objectName: "menuMinimizeGroup"
                }

                MenuItem {
                    objectName: "menuMinimizeNormally"
                    text: qsTr("Minimize normally")
                    checkable: true
                    exclusiveGroup: menuMinimizeGroup
                }

                MenuItem {
                    visible: platform != 'Darwin'
                    objectName: "menuMinimizeToTray"
                    text: qsTr("Minimize to tray")
                    checkable: true
                    exclusiveGroup: menuMinimizeGroup
                }

                MenuItem {
                    objectName: "menuMinimizeNormallyManually"
                    text: qsTr("Manual only: Minimize normally")
                    checkable: true
                    exclusiveGroup: menuMinimizeGroup
                }

                MenuItem {
                    visible: platform != 'Darwin'
                    objectName: "menuMinimizeToTrayManually"
                    text: qsTr("Manual only: Minimize to tray")
                    checkable: true
                    exclusiveGroup: menuMinimizeGroup
                }
            }

            Menu {
                title: qsTr("Automatic updates")

                MenuItem {
                    objectName: "menuEnableUpdateCheck"
                    text: qsTr("Automatically check for Pext updates")
                    checkable: true
                    visible: internalUpdaterEnabled
                }

                MenuItem {
                    id: menuEnableObjectUpdateCheck
                    objectName: "menuEnableObjectUpdateCheck"
                    text: qsTr("Automatically check for module and theme updates")
                    checkable: true
                }

                MenuItem {
                    objectName: "menuEnableObjectUpdateInstall"
                    text: qsTr("Automatically install module and theme updates")
                    checkable: true
                    enabled: menuEnableObjectUpdateCheck.checked
                }
            }

            MenuItem {
                visible: platform != 'Darwin'
                objectName: "menuEnableGlobalHotkey"
                text: qsTr("Move Pext to the foreground when global hotkey is pressed (%1)").arg("Ctrl+`")
                checkable: true
            }

            MenuItem {
                objectName: "menuShowTrayIcon"
                text: qsTr("Always show tray icon")
                checkable: true
            }
        }

        Menu {
            title: qsTr("&Help")

            MenuItem {
                objectName: "menuAbout"
                text: platform == 'Darwin' ? "About" : qsTr("About")
                onTriggered: {
                    var aboutDialog = Qt.createComponent("AboutDialog.qml");
                    aboutDialog.createObject(applicationWindow,
                        {"locales": locales});
                }
            }

            MenuItem {
                objectName: "menuCheckForUpdates"
                text: qsTr("Check for updates")
            }

            MenuItem {
                visible: platform == 'Darwin'
                objectName: "menuInstallQuickActionService"
                text: qsTr("Install quick action service")
            }

            MenuItem {
                objectName: "menuHomepage"
                text: qsTr("Visit homepage")
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin

        Repeater {
            id: actionableRepeater
            objectName: "actionableRepeater"
            signal activateActionable(int index);
            onActivateActionable: {
                var actionable = actionables[index]
                if (actionable.buttonUrl.startsWith("pext:")) {
                    applicationWindow.internalCall(actionable.buttonUrl)
                } else {
                    Qt.openUrlExternally(actionable.buttonUrl)
                }
                actionableRepeater.removeActionable(index)
            }
            signal removeActionable(int index);

            model: actionables
            height: childrenRect.height

            Rectangle {
                color: {
                    if (modelData.urgency == "high") {
                        return "red"
                    } else {
                        return "#FAFAD2"
                    }
                }
                Layout.fillWidth: true
                Layout.preferredHeight: row.height

                RowLayout {
                    id: row
                    width: parent.width
                    Layout.preferredHeight: childrenRect.height

                    Text {
                        text: modelData.text
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        verticalAlignment: Text.AlignVCenter
                    }

                    Button {
                        id: button
                        visible: modelData.buttonText
                        text: modelData.buttonText
                        Layout.fillHeight: true
                        onClicked: actionableRepeater.activateActionable(index)
                    }

                    Text {
                        text: "<a href='#' style='text-decoration:none;'>❌</a>"
                        textFormat: Text.RichText
                        Layout.fillHeight: true
                        verticalAlignment: Text.AlignVCenter
                        onLinkActivated: actionableRepeater.removeActionable(index)
                    }
                }
            }
        }

        GridLayout {
            Layout.fillHeight: true

            Button {
                enabled: tabs.count > 0 && tabs.getTab(tabs.currentIndex) != null && tabs.getTab(tabs.currentIndex).item != null && (searchInput.length > 0 || tabs.getTab(tabs.currentIndex).item.children[0].children[2].contentItem.tree.length > 0 || tabs.getTab(tabs.currentIndex).item.children[0].children[0].visible)

                text: "←"
                objectName: "backButton"
            }

            TextField {
                enabled: tabs.count > 0
                placeholderText: tabs.count > 0 ? qsTr("Type to search") : ""
                id: searchInput
                objectName: "searchInputModel"

                focus: true

                onFocusChanged: {
                    focus = true
                }

                Layout.fillWidth: true
            }

            Button {
                text: "➕"
                onClicked: menuLoadModule.trigger()
            }

            Button {
                visible: tabs.count > 0
                text: "❌"
                onClicked: menuCloseActiveModule.trigger()
            }

            Button {
                visible: tabs.count > 0
                text: "☰"
                onClicked: openContextMenu();
            }
        }

        TabView {
            visible: tabs.count > 0
            id: tabs
            objectName: "tabs"

            signal disableRequest(int index, int reason);
            signal updateStateRequest(int index, string state);
            signal removeRequest(int index);

            onDisableRequest: {
                tabs.getTab(index).item.disableReason = reason;
                tabs.getTab(index).item.progressStates = [];
            }

            onUpdateStateRequest: {
                var disableReason = tabs.getTab(index).item.disableReason;
                tabs.getTab(index).item.progressStates.push(state);

                // Forcefully ensure redraw
                tabs.getTab(index).item.disableReason = 0;
                tabs.getTab(index).item.disableReason = disableReason;
            }

            onRemoveRequest: {
                tabs.getTab(index).sourceComponent = undefined;
                tabs.removeTab(index);
            }

            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        Image {
            id: logo
            visible: tabs.count == 0
            asynchronous: true
            source: "../images/scalable/logo.svg"
            fillMode: Image.Pad
            horizontalAlignment: Image.AlignHCenter
            verticalAlignment: Image.AlignVCenter
            Layout.fillWidth: true
            Layout.minimumHeight: sourceSize.height
            Layout.minimumWidth: sourceSize.width
        }

        TextEdit {
            objectName: "introScreen"
            visible: tabs.count == 0

            text: "<h2>" + qsTr("Hotkey reference") + "</h2>"

            color: palette.text
            textFormat: TextEdit.RichText
            readOnly: true
            selectByMouse: false
            wrapMode: TextEdit.Wrap
            horizontalAlignment: TextEdit.AlignHCenter
            verticalAlignment: TextEdit.AlignVCenter
            Layout.fillWidth: true
            padding: 10
        }

        Grid {
            visible: tabs.count == 0
            horizontalItemAlignment: Grid.AlignHCenter
            verticalItemAlignment: Grid.AlignTop
            flow: Grid.TopToBottom
            spacing: 15
            Layout.fillHeight: true
            Layout.alignment: Qt.AlignHCenter

            Repeater {
                id: hotkeyRepeater
                objectName: "hotkeyRepeater"

                property var hotkeys: {
                    "window": {
                        "text": qsTr("Pext"),
                        "foreground": {
                            "text": qsTr("Move Pext to the foreground"),
                            "hotkeys": ["Ctrl+`"],
                            "unsupported_on": ["Darwin", "Windows"]
                        },
                        "minimize": {
                            "text": qsTr("Minimize"),
                            "hotkeys": [escapeShortcut.nativeText]
                        },
                        "back_and_minimize": {
                            "text": qsTr("Go back to module's base level and minimize"),
                            "hotkeys": [shiftEscapeShortcut.nativeText]
                        },
                        "tab_complete": {
                            "text": qsTr("Complete input"),
                            "hotkeys": [tabShortcut.nativeText]
                        }
                    },
                    "tabs": {
                        "text": qsTr("Tabs"),
                        "open": {
                            "text": qsTr("Open a new tab"),
                            "hotkeys": [menuLoadModule.shortcut]
                        },
                        "reload": {
                            "text": qsTr("Reload active tab"),
                            "hotkeys": [menuReloadActiveModule.shortcut]
                        },
                        "close": {
                            "text": qsTr("Close active tab"),
                            "hotkeys": [menuCloseActiveModule.shortcut]
                        },
                        "next": {
                            "text": qsTr("Switch to next tab"),
                            "hotkeys": [nextTabShortcut.nativeText]
                        },
                        "previous": {
                            "text": qsTr("Switch to previous tab"),
                            "hotkeys": [previousTabShortcut.nativeText]
                        }
                    },
                    "module": {
                        "text": qsTr("Modules"),
                        "back": {
                            "text": qsTr("Go back"),
                            "hotkeys": [escapeShortcut.nativeText]
                        },
                        "activate_entry": {
                            "text": qsTr("Activate highlighted entry"),
                            "hotkeys": [enterShortcut.nativeText, qsTr("Left mouse button")]
                        },
                        "activate_entry_nominimize": {
                            "text": qsTr("Activate highlighted entry (never minimize)"),
                            "hotkeys": [noMinimizeShortcut.nativeText, qsTr("Middle mouse button")]
                        },
                        "enter_arguments": {
                            "text": qsTr("Enter arguments for highlighted command"),
                            "hotkeys": [argsShortcut.nativeText, qsTr("Right mouse button")]
                        },
                        "context_menu": {
                            "text": qsTr("Open context menu"),
                            "hotkeys": [contextMenuShortcut.nativeText, qsTr("Right mouse button")]
                        },
                        "sorting": {
                            "text": qsTr("Change sorting style"),
                            "hotkeys": [changeSortModeShortcut.nativeText]
                        }
                    },
                    "actionables": {
                        "text": qsTr("Alerts"),
                        "activate": {
                            "text": qsTr("Accept"),
                            "hotkeys": [activateActionableShortcut.nativeText]
                        },
                        "dismiss": {
                            "text": qsTr("Decline"),
                            "hotkeys": [dismissActionableShortcut.nativeText]
                        }
                    }
                }

                model: Object.keys(hotkeys)

                TextEdit {
                    text: {
                        var string = "<h3>" + hotkeyRepeater.hotkeys[modelData].text + "</h3>";

                        for (const key of Object.keys(hotkeyRepeater.hotkeys[modelData])) {
                            var data = hotkeyRepeater.hotkeys[modelData][key];
                            if (!data.text || !data.hotkeys) {
                                continue;
                            }
                            if (data.unsupported_on && data.unsupported_on.indexOf(platform) != -1) {
                                continue;
                            }
                            string += "<p><b>" + data.hotkeys.join(' / ') + "</b><br>" + data.text + "</p>";
                        }

                        return string;
                    }

                    color: palette.text
                    textFormat: TextEdit.RichText
                    readOnly: true
                    selectByMouse: false
                    wrapMode: TextEdit.Wrap
                }
            }
        }
    }

    statusBar: StatusBar {
        RowLayout {
            width: parent.width

            Label {
                id: statusText
                objectName: "statusText"
                Layout.fillWidth: true
            }

            Label {
                visible: statusText.text
                text: "|"
            }

            Label {
                id: statusSortMode
                objectName: "statusSortMode"

                signal sortModeChanged()
                onSortModeChanged: {
                    var tab = tabs.getTab(tabs.currentIndex);
                    if (tab == null || tab.item == null || tab.item.children[0] == null) { return ''; };
                    tab.item.children[0].children[2].contentItem.sortModeChanged();
                }

                text: {
                    var tab = tabs.getTab(tabs.currentIndex);
                    if (tab == null || tab.item == null || tab.item.children[0] == null) { return ''; };
                    var sortMode = tab.item.children[0].children[2].contentItem.pextSortMode;
                    if (sortMode == 'Module') {
                        return qsTr("Sort: Module");
                    } else if (sortMode == 'Ascending') {
                        return qsTr("Sort: Ascending");
                    } else if (sortMode == 'Descending') {
                        return qsTr("Sort: Descending");
                    } else {
                        return sortMode;
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton

                    hoverEnabled: true

                    onClicked: statusSortMode.sortModeChanged()
                }
            }

            Label {
                visible: statusSortMode.text
                text: "|"
            }

            Label {
                objectName: "statusQueue"

                text: {
                    var unprocessedForeground = 0;
                    var unprocessedBackground = 0;
                    var hasEntriesForeground = true;
                    for (var i = 0; i < tabs.count; i++) {
                        var tab = tabs.getTab(i);
                        if (tab == null || tab.item == null || tab.item.children[0] == null) { continue; };
                        var unprocessedCount = tab.item.children[0].children[2].contentItem.unprocessedQueueCount;
                        if (i == tabs.currentIndex) {
                            unprocessedForeground = unprocessedCount;
                            hasEntriesForeground = tab.item.children[0].children[2].contentItem.hasEntries;
                        } else {
                            unprocessedBackground += unprocessedCount;
                        }
                    }

                    if (unprocessedForeground > 0 || unprocessedBackground > 0) {
                        return qsTr("Processing: %1 (%2)").arg(unprocessedForeground).arg(unprocessedBackground);
                    } else if (hasEntriesForeground) {
                        return qsTr("Ready");
                    } else {
                       qsTr("Waiting");
                    }
                }
            }
        }
    }

    property string tr_module_class_does_not_implement_modulebase: qsTr("Module's Module class does not implement ModuleBase")
    property string tr_module_failed_load_wrong_param_count: qsTr("Failed to load module {0}: {1} function has {2} parameters (excluding self), expected {3}")
    property string tr_already_installed: qsTr("{0} is already installed")
    property string tr_downloading_from_url: qsTr("Downloading {0} from {1}")
    property string tr_failed_to_download: qsTr("Failed to download {0}: {1}")
    property string tr_downloading_dependencies: qsTr("Downloading dependencies for {0}")
    property string tr_failed_to_download_dependencies: qsTr("Failed to download dependencies for {0}")
    property string tr_installed: qsTr("Installed {0}")
    property string tr_uninstalling: qsTr("Uninstalling {0}")
    property string tr_already_uninstalled: qsTr("{0} is already uninstalled")
    property string tr_uninstalled: qsTr("Uninstalled {0}")
    property string tr_updating: qsTr("Updating {0}")
    property string tr_already_up_to_date: qsTr("{0} is already up to date")
    property string tr_failed_to_download_update: qsTr("Failed to download update for {0}: {1}")
    property string tr_updating_dependencies: qsTr("Updating dependencies for {0}")
    property string tr_failed_to_update_dependencies: qsTr("Failed to update dependencies for {0}")
    property string tr_updated: qsTr("Updated {0}")
    property string tr_checking_for_pext_updates: qsTr("Checking for Pext updates")
    property string tr_failed_to_check_for_pext_updates: qsTr("Failed to check for Pext updates: {0}")
    property string tr_pext_is_already_up_to_date: qsTr("Pext is already up-to-date")
    property string tr_failed_to_check_for_module_update: qsTr("Failed to check for updates for module {0}: {1}")
    property string tr_data_queued_for_typing: qsTr("Data queued for typing")
    property string tr_queued_data_typed: qsTr("All queued data has been typed")
    property string tr_data_queued_for_clipboard: qsTr("Data queued for clipboard")
    property string tr_data_copied_to_clipboard: qsTr("Data copied to clipboard")
    property string tr_enter_arguments: qsTr("Enter arguments")
    property string tr_no_context_menu_available: qsTr("No context menu available")
    property string tr_no_tab_completion_possible: qsTr("No tab completion possible")
    property string tr_no_entry_selected: qsTr("No entry selected")
    property string tr_no_command_available_for_current_filter: qsTr("No command available for current filter")
    property string tr_pynput_is_unavailable: qsTr("Pynput is unavailable")
    property string tr_pyautogui_is_unavailable: qsTr("PyAutoGUI is unavailable")

    property string tr_actionable_update_check_enabled: qsTr("Automatic update checks are enabled. You can change this in settings.")
    property string tr_actionable_update_available: qsTr("Pext {0} is available. You are currently running Pext {1}.")
    property string tr_actionable_update_available_button: qsTr("Open download page")
    property string tr_actionable_object_update_available: qsTr("{0} can be updated.")
    property string tr_actionable_object_update_available_button: qsTr("Update")
    property string tr_actionable_object_update_available_in_use: qsTr("{0} can be updated but is currently in use.")
    property string tr_actionable_object_update_available_in_use_button: qsTr("Update and reload")
    property string tr_actionable_error_in_module: qsTr("An error occured in {0}: {1}.")
    property string tr_actionable_report_error_in_module: qsTr("Report as bug")
}
