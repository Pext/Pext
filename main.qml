/*
    This file is part of PyPass

    PyPass is free software: you can redistribute it and/or modify
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
    title: 'PyPass'
    property int margin: 10
    width: Screen.width
    height: searchInput.height + resultList.contentHeight + errorMessage.height + 3 * margin
    maximumHeight: 0.5 * Screen.height

    flags: Qt.FramelessWindowHint | Qt.Window

    Behavior on height {
        PropertyAnimation {
            duration: 50
        }
    }

    function moveUp() {
        if (resultList.currentIndex > 0)
            resultList.currentIndex -= 1
    }

    function moveDown() {
        if (resultList.currentIndex < resultList.maximumIndex)
            resultList.currentIndex += 1
    }

    Shortcut {
        sequence: "Up"
        onActivated: moveUp()
    }

    Shortcut {
        sequence: "Ctrl+K"
        onActivated: moveUp()
    }

    Shortcut {
        sequence: "Down"
        onActivated: moveDown()
    }

    Shortcut {
        sequence: "Ctrl+J"
        onActivated: moveDown()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin
        RowLayout {
            Layout.fillWidth: true
            TextField {
                id: searchInput
                objectName: "searchInputModel"

                font.pixelSize: 24
                focus: true

                Layout.fillWidth: true
            }
        }
        ScrollView {
            Layout.fillHeight: true
            Layout.fillWidth: true

            ListView {
                id: resultList
                objectName: "resultListModel"

                property int maximumIndex: resultListModelMaxIndex
                property bool makeItalic: resultListModelMakeItalic

                model: resultListModel

                delegate: Text { 
                    text: display
                    textFormat: Text.PlainText
                    font.pixelSize: 18
                    font.italic: resultList.makeItalic && text.indexOf(' ') >= 0 ? true : false
                    color: resultList.currentIndex === index ? "red" : "steelblue"
                    Behavior on color { PropertyAnimation {} }
                }

                Layout.fillHeight: true
                Layout.fillWidth: true
            }
        }
        Text {
            id: errorMessage

            text: errorMessageModelText

            Timer {
                objectName: "clearErrorMessageTimer"

                interval: 1000;
                running: true;
                repeat: true;
            }

            lineHeight: errorMessageModelLineHeight

            color: "red"
        }
    }
}
