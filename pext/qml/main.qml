/*
    Copyright (c) 2015 - 2018 Sylvia van Os <sylvia@hackerchick.me>

    This file is part of Pext

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

import QtQuick 2.5
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0

ApplicationWindow {
    id: applicationWindow
    title: applicationTitle
    property bool internalUpdaterEnabled: USE_INTERNAL_UPDATER
    property string version: applicationVersion
    property string platform: systemPlatform
    property int margin: 10
    minimumWidth: 500
    minimumHeight: 300
    width: Screen.width
    height: 300

    flags: Qt.Window

    SystemPalette { id: palette; colorGroup: SystemPalette.Active }

    Item {
        objectName: "permissionRequests"

        signal updatePermissionRequest()
        signal updatePermissionRequestAccepted()
        signal updatePermissionRequestRejected()

        onUpdatePermissionRequest: {
            var permissionRequestDialog = Qt.createComponent("UpdatePermissionDialog.qml");
            permissionRequestDialog.createObject(applicationWindow,
                {"requestAccepted": updatePermissionRequestAccepted,
                 "requestRejected": updatePermissionRequestRejected});
        }
    }

    Item {
        objectName: "updateAvailableRequests"

        signal showUpdateAvailableDialog()
        signal updateAvailableDialogAccepted()

        onShowUpdateAvailableDialog: {
            var updateAvailableDialogRequestDialog = Qt.createComponent("UpdateAvailableDialog.qml");
            updateAvailableDialogRequestDialog.createObject(applicationWindow,
                {"updateAccepted": updateAvailableDialogAccepted});
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

    function openBaseMenu() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        tab.item.children[0].children[2].contentItem.openBaseMenu();
    }

    function openContextMenu() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        tab.item.children[0].children[2].contentItem.openContextMenu();
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
        objectName: "escapeShortcut"
        sequence: "Escape"
    }

    Shortcut {
        objectName: "tabShortcut"
        sequence: "Tab"
    }

    Shortcut {
        sequence: "Ctrl+Shift+."
        onActivated: openBaseMenu();
    }

    Shortcut {
        sequence: "Ctrl+."
        onActivated: openContextMenu();
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

    Shortcut {
        sequence: "Ctrl+Tab"
        onActivated: nextTab()
    }

    Shortcut {
        sequence: "Ctrl+Shift+Tab" // StandardKey.PreviousChild does not work on my machine
        onActivated: prevTab()
    }

    Shortcut {
        sequence: "Alt+1"
        onActivated: switchTab(0)
    }

    Shortcut {
        sequence: "Alt+2"
        onActivated: switchTab(1)
    }

    Shortcut {
        sequence: "Alt+3"
        onActivated: switchTab(2)
    }

    Shortcut {
        sequence: "Alt+4"
        onActivated: switchTab(3)
    }

    Shortcut {
        sequence: "Alt+5"
        onActivated: switchTab(4)
    }

    Shortcut {
        sequence: "Alt+6"
        onActivated: switchTab(5)
    }

    Shortcut {
        sequence: "Alt+7"
        onActivated: switchTab(6)
    }

    Shortcut {
        sequence: "Alt+8"
        onActivated: switchTab(7)
    }

    Shortcut {
        sequence: "Alt+9"
        onActivated: switchTab(8)
    }

    Shortcut {
        sequence: "Alt+0"
        onActivated: switchTab(9)
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

            MenuItem {
                objectName: "menuReloadActiveModule"
                text: qsTr("Reload active module")
                shortcut: StandardKey.Refresh
            }

            MenuItem {
                id: menuCloseActiveModule
                objectName: "menuCloseActiveModule"
                text: qsTr("Close active module")
                shortcut: StandardKey.Close
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
                        var noModulesInstalledDialog = Qt.createComponent("NoModulesInstalledDialog.qml");
                        noModulesInstalledDialog.createObject(applicationWindow);
                    } else {
                        var loadModuleDialog = Qt.createComponent("LoadModuleDialog.qml");
                        loadModuleDialog.createObject(applicationWindow,
                            {"modules": modules,
                             "loadRequest": loadModuleRequest,
                             "modulesPath": modulesPath});
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
                    text: qsTr("From online module list")

                    property var repositories:
                        [{
                          "name": "Pext team",
                          "url": "https://pext.hackerchick.me/modules_v2.json"
                        }, {
                          "name": "Other developers",
                          "url": "https://pext.hackerchick.me/third_party_modules_v2.json"
                        }]

                    onTriggered: {
                        var installModuleFromRepositoryDialog = Qt.createComponent("InstallFromRepositoryDialog.qml");
                        installModuleFromRepositoryDialog.createObject(applicationWindow,
                            {"installedObjects": modules,
                             "installRequest": menuInstallModule.installModuleRequest,
                             "repositories": repositories,
                             "type": "modules"})
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
                        var noThemesInstalledDialog = Qt.createComponent("NoThemesInstalledDialog.qml");
                        noThemesInstalledDialog.createObject(applicationWindow);
                    } else {
                        var loadThemeDialog = Qt.createComponent("LoadThemeDialog.qml");
                        loadThemeDialog.createObject(applicationWindow,
                            {"currentTheme": currentTheme,
                             "themes": themes,
                             "loadRequest": loadThemeRequest,
                             "themesPath": themesPath});
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
                    text: qsTr("From online theme list")

                    property var repositories:
                        [{
                          "name": "Pext team",
                          "url": "https://pext.hackerchick.me/themes_v2.json"
                        }, {
                          "name": "Other developers",
                          "url": "https://pext.hackerchick.me/third_party_themes_v2.json"
                        }]

                    onTriggered: {
                        var installThemeFromRepositoryDialog = Qt.createComponent("InstallFromRepositoryDialog.qml");
                        installThemeFromRepositoryDialog.createObject(applicationWindow,
                            {"installedObjects": themes,
                             "installRequest": menuInstallTheme.installThemeRequest,
                             "repositories": repositories,
                             "type": "themes"})
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
            }

            Menu {
                title: qsTr("Sorting style")

                ExclusiveGroup {
                    id: menuSortGroup
                    objectName: "menuSortGroup"
                }

                MenuItem {
                    objectName: "menuSortModule"
                    text: qsTr("Sort by module choice")
                    checkable: true
                    exclusiveGroup: menuSortGroup
                }

                MenuItem {
                    objectName: "menuSortAscending"
                    text: qsTr("Sort ascending")
                    checkable: true
                    exclusiveGroup: menuSortGroup
                }

                MenuItem {
                    objectName: "menuSortDescending"
                    text: qsTr("Sort descending")
                    checkable: true
                    exclusiveGroup: menuSortGroup
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
                    objectName: "menuEnableObjectUpdateCheck"
                    text: qsTr("Automatically update modules and themes")
                    checkable: true
                }
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
                objectName: "menuHomepage"
                text: qsTr("Visit homepage")
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin

        GridLayout {
            Layout.fillHeight: true

            Button {
                anchors.top: parent.top
                anchors.bottom: parent.bottom

                enabled: tabs.count > 0 && tabs.getTab(tabs.currentIndex) != null && tabs.getTab(tabs.currentIndex).item != null && (searchInput.length > 0 || tabs.getTab(tabs.currentIndex).item.children[0].children[2].contentItem.depth > 0 || tabs.getTab(tabs.currentIndex).item.children[0].children[0].visible)

                width: 60
                text: searchInput.length > 0 ? qsTr("Clear") : qsTr("Back")
                objectName: "backButton"
            }

            TextField {
                anchors.top: parent.top
                anchors.bottom: parent.bottom

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
        }

        TabView {
            visible: tabs.count > 0
            id: tabs
            objectName: "tabs"

            signal removeRequest(int index);

            onRemoveRequest: {
                tabs.getTab(index).sourceComponent = undefined;
                tabs.removeTab(index);
            }

            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        GridLayout {
            flow: applicationWindow.width > applicationWindow.height ? GridLayout.LeftToRight : GridLayout.TopToBottom
            visible: tabs.count == 0

            TextEdit {
                text: "<h2>" + qsTr("Design philosophy") + "</h2>" +
                      "<p>" + qsTr("Pext is designed to stay out of your way. As soon as a module deems you are done using it, Pext will hide itself to the system tray. If you need to reach Pext again after it hid itself, just start it again or open it from the system tray.") + "</p>"

                color: palette.text
                textFormat: TextEdit.RichText
                readOnly: true
                selectByMouse: false
                wrapMode: TextEdit.Wrap
                horizontalAlignment: TextEdit.AlignHCenter
                verticalAlignment: TextEdit.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
            }

            Image {
                id: logo
                visible: if (parent.flow == GridLayout.LeftToRight) {
                    return applicationWindow.width > 3 * sourceSize.width
                } else {
                    return applicationWindow.height > 4 * sourceSize.height
                }
                asynchronous: true
                source: "../images/scalable/logo.svg"
                fillMode: Image.Pad
                horizontalAlignment: Image.AlignHCenter
                verticalAlignment: Image.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
                Layout.minimumHeight: sourceSize.height + 50
                Layout.minimumWidth: sourceSize.width + 50
            }

            Rectangle {
                visible: !logo.visible
                width: 50
            }

            TextEdit {
                objectName: "introScreen"

                property int modulesInstalledCount

                text: "<h2>" + qsTr("Getting started") + "</h2>" +
                      "<p>" + qsTr("To get started, press <kbd>%1</kbd> to open a new tab. When you are done with a tab, you can always close it by pressing <kbd>%2</kbd>. You currently have %n module(s) installed. You can manage modules in the Module menu.", "", modulesInstalledCount).arg(menuLoadModule.shortcut).arg(menuCloseActiveModule.shortcut) + "</p>"

                color: palette.text
                textFormat: TextEdit.RichText
                readOnly: true
                selectByMouse: false
                wrapMode: TextEdit.Wrap
                horizontalAlignment: TextEdit.AlignHCenter
                verticalAlignment: TextEdit.AlignVCenter
                Layout.fillHeight: true
                Layout.fillWidth: true
            }
        }
    }

    statusBar: StatusBar {
        RowLayout {
            width: parent.width

            Label {
                objectName: "statusText"
                Layout.fillWidth: true
            }

            Label {
                objectName: "statusQueue"

                property var entriesLeftForeground
                property var entriesLeftBackground

                anchors.right: parent.right

                text: entriesLeftForeground || entriesLeftBackground ?
                      qsTr("Processing: %1 (%2)").arg(entriesLeftForeground).arg(entriesLeftBackground) :
                      tabs.getTab(tabs.currentIndex) != null && tabs.getTab(tabs.currentIndex).item != null && !tabs.getTab(tabs.currentIndex).item.children[0].children[2].contentItem.hasEntries ?
                      qsTr("Waiting") : qsTr("Ready")
            }
        }
    }
}
