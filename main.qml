/*
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
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0

ApplicationWindow {
    id: applicationWindow
    title: 'Pext'
    property int margin: 10
    width: Screen.width
    height: 0.3 * Screen.height

    flags: Qt.FramelessWindowHint | Qt.Window

    function nextTab() {
        if (tabs.currentIndex < tabs.count - 1)
                tabs.currentIndex += 1
        else
                tabs.currentIndex = 0
    }

    function prevTab() {
        if (tabs.currentIndex > 0)
                tabs.currentIndex -= 1
        else
                tabs.currentIndex = tabs.count - 1
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
        objectName: "upShortcut"
        sequence: "Up"
    }

    Shortcut {
        objectName: "upShortcutAlt"
        sequence: "Ctrl+K"
    }

    Shortcut {
        objectName: "downShortcut"
        sequence: "Down"
    }

    Shortcut {
        objectName: "downShortcutAlt"
        sequence: "Ctrl+J"
    }

    Shortcut {
        sequence: "Ctrl+Tab"
        onActivated: nextTab()
    }

    Shortcut {
        sequence: "Ctrl+Shift+Tab"
        onActivated: prevTab()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin
        TextField {
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
            id: tabs
            objectName: "tabs"

            Layout.fillWidth: true
        }
        ListView {
             id: messageListModel
             model: messageListModelList

             delegate: Text {
                 text: display
                 textFormat: Text.StyledText
             }

             Layout.fillHeight: true
             Layout.fillWidth: true
             Layout.minimumHeight: contentHeight
         }
    }

    Timer {
        objectName: "clearOldMessagesTimer"

        interval: 1000
        running: true
        repeat: true
    }
}
