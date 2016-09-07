/*
    Copyright (c) 2016 Sylvia van Os <iamsylvie@openmailbox.org>

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
import QtQuick.Controls 1.0
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0

ApplicationWindow {
    id: applicationWindow
    property int margin: 10
    width: Screen.width
    height: 0.3 * Screen.height

    flags: Qt.FramelessWindowHint | Qt.Window

    function pageUp() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        var listView = tab.item.contentItem;
        listView.currentIndex = listView.currentIndex - (listView.height / 23) + 1;

        if (listView.currentIndex < 0)
            listView.currentIndex = 0;

        listView.positionViewAtIndex(listView.currentIndex, ListView.Beginning);
    }

    function pageDown() {
        var tab = tabs.getTab(tabs.currentIndex);
        if (typeof tab === "undefined")
            return;

        var listView = tab.item.contentItem;
        listView.currentIndex = listView.currentIndex + (listView.height / 23);
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
        objectName: "reloadModuleShortcut"
        sequence: "F5"
    }

    Shortcut {
        sequence: "Up"
        onActivated: tabs.getTab(tabs.currentIndex).item.contentItem.decrementCurrentIndex()
    }

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: tabs.getTab(tabs.currentIndex).item.contentItem.decrementCurrentIndex()
    }

    Shortcut {
        sequence: "Down"
        onActivated: tabs.getTab(tabs.currentIndex).item.contentItem.incrementCurrentIndex()
    }

    Shortcut {
        sequence: "Ctrl+J"
        onActivated: tabs.getTab(tabs.currentIndex).item.contentItem.incrementCurrentIndex()
    }

    Shortcut {
        sequence: "PgUp"
        onActivated: pageUp()
    }

    Shortcut {
        sequence: "Ctrl+B"
        onActivated: pageUp()
    }

    Shortcut {
        sequence: "PgDown"
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
        sequence: "Ctrl+Shift+Tab"
        onActivated: prevTab()
    }

    Shortcut {
        objectName: "openTabShortcut"
        sequence: "Ctrl+T"
    }

    Shortcut {
        objectName: "closeTabShortcut"
        sequence: "Ctrl+W"
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

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin
        RowLayout {
            TextField {
                enabled: tabs.count > 0
                placeholderText: tabs.count > 0 ? "Type to search" : ""
                id: searchInput
                objectName: "searchInputModel"

                font.pixelSize: 24
                focus: true

                onFocusChanged: {
                    focus = true
                }

                Layout.fillWidth: true
            }

            Button {
                Layout.preferredWidth: searchInput.height
                Layout.preferredHeight: searchInput.height

                iconName: "preferences-system"
                iconSource: "icons/Gnome-preferences-system.svg" // Fallback
                onClicked: settingsMenu.popup()
            }

            Menu {
                id: settingsMenu

                MenuItem {
                    objectName: "menuListModules"
                    text: "List installed modules"
                }

                MenuItem {
                    objectName: "menuInstallModule"
                    text: "Install module"
                }

                MenuItem {
                    objectName: "menuUninstallModule"
                    text: "Uninstall module"
                }

                MenuItem {
                    objectName: "menuUpdateModule"
                    text: "Update module"
                }

                MenuItem {
                    objectName: "menuUpdateAllModules"
                    text: "Update all modules"
                }

                MenuSeparator { }

                MenuItem {
                    objectName: "menuAbout"
                    text: "About"
                }

                MenuSeparator { }

                MenuItem {
                    objectName: "menuQuit"
                    text: "Quit"
                }
            }
        }

        TabView {
            visible: tabs.count > 0
            id: tabs
            objectName: "tabs"

            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        TextArea {
            objectName: "introScreen"
            property var modulesInstalledCount
            visible: tabs.count == 0
            text: "<h1>Welcome to Pext</h1>" +
                  "<p>To get started, press <kbd>Ctrl+T</kbd> to open a new " +
                  "tab.</p>" +
                  "<p>When you are done with a tab, you can always close it " +
                  "by pressing <kbd>Ctrl+W</kbd>.</p>" +
                  "<p>You currently have " + modulesInstalledCount + " module" +
                  (modulesInstalledCount == 1 ? "" : "s") + " installed. You " +
                  "can manage modules in the settings menu."

            textFormat: TextEdit.RichText
            backgroundVisible: false
            readOnly: true
            selectByMouse: false
            menu: null
            horizontalAlignment: TextEdit.AlignHCenter
            Layout.fillWidth: true
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
                anchors.right: parent.right
            }
        }
    }
}
