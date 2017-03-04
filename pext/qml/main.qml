/*
    Copyright (c) 2016 - 2017 Sylvia van Os <sylvia@hackerchick.me>

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
    property string version: applicationVersion
    property int margin: 10
    width: Screen.width
    height: 0.3 * Screen.height

    flags: Qt.Window

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
            title: "&Pext"

            MenuItem {
                objectName: "menuQuit"
                text: "Quit"
                shortcut: "Ctrl+Q"
            }

            MenuItem {
                objectName: "menuQuitWithoutSaving"
                text: "Quit without saving"
                shortcut: "Ctrl+Shift+Q"
            }
        }

        Menu {
            title: "&Module"

            MenuItem {
                objectName: "menuReloadActiveModule"
                text: "Reload active module"
                shortcut: "F5"
            }

            MenuItem {
                objectName: "menuCloseActiveModule"
                text: "Close active module"
                shortcut: "Ctrl+W"
            }

            MenuSeparator { }

            MenuItem {
                objectName: "menuLoadModule"
                text: "Load module"
                shortcut: "Ctrl+T"
            }

            MenuItem {
                objectName: "menuListModules"
                text: "List installed modules"
            }

            Menu {
                title: "Install module"

                MenuItem {
                    objectName: "menuInstallModuleFromRepository"
                    text: "From online module list"
                }

                MenuItem {
                    objectName: "menuInstallModuleFromURL"
                    text: "From URL"
                }
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
        }

        Menu {
            title: "&Help"

            MenuItem {
                objectName: "menuAbout"
                text: "About"
                onTriggered: {
                    var aboutDialog = Qt.createComponent("AboutDialog.qml");
                    aboutDialog.createObject(applicationWindow);
                }
            }

            MenuItem {
                objectName: "menuHomepage"
                text: "Visit homepage"
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin
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

        TabView {
            visible: tabs.count > 0
            id: tabs
            objectName: "tabs"

            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        GridLayout {
            flow: applicationWindow.width > 900 ? GridLayout.LeftToRight : GridLayout.TopToBottom
            visible: tabs.count == 0

            Image {
                asynchronous: true
                source: "../images/scalable/logo.svg"
                fillMode: Image.Pad
                horizontalAlignment: Image.AlignHCenter
                verticalAlignment: Image.AlignVCenter
                anchors.margins: margin
                Layout.fillHeight: true
                Layout.fillWidth: true
            }

            TextEdit {
                objectName: "introScreen"
                property var modulesInstalledCount
                text: "<h1>Welcome to Pext</h1>" +
                      "<p>To get started, press <kbd>Ctrl+T</kbd> to open a new " +
                      "tab.</p>" +
                      "<p>When you are done with a tab, you can always close it " +
                      "by pressing <kbd>Ctrl+W</kbd>.</p>" +
                      "<p>You currently have " + modulesInstalledCount + " module" +
                      (modulesInstalledCount == 1 ? "" : "s") + " installed. You " +
                      "can manage modules in the settings menu."

                textFormat: TextEdit.RichText
                readOnly: true
                selectByMouse: false
                textMargin: 0
                horizontalAlignment: TextEdit.AlignHCenter
                verticalAlignment: TextEdit.AlignVCenter
                anchors.margins: margin
                Layout.fillHeight: true
                Layout.fillWidth: true
            }

            Layout.fillHeight: true
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
