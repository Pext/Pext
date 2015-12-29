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
    height: 0.3 * Screen.height

    flags: Qt.FramelessWindowHint | Qt.Window

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
        ScrollView {
            Layout.fillHeight: true
            Layout.fillWidth: true

            ListView {
                id: resultList
                objectName: "resultListModel"

                property int maximumIndex: resultListModelMaxIndex
                property bool makeItalic: resultListModelMakeItalic

                model: resultListModel

                delegate: Component {
                    Item {
                        property variant itemData: model.modelData
                        width: parent.width
                        height: 23
                        Column {
                             Text {
                                text: display
                                textFormat: Text.PlainText
                                font.pixelSize: 18
                                font.italic: resultList.makeItalic && text.indexOf(' ') >= 0 ? true : false
                                color: resultList.currentIndex === index ? "red" : "steelblue"
                                Behavior on color { PropertyAnimation {} }
                            }
                        }
                        MouseArea {
                            objectName: "resultListMouseModel"
                            anchors.fill: parent

                            hoverEnabled: true

                            onPositionChanged: {
                                if (index <= resultListModelMaxIndex)
                                    resultList.currentIndex = index
                            }
                            onClicked: {
                                if (index <= resultListModelMaxIndex)
                                    searchInput.accepted()
                            }
                        }
                    }
                }
            }
        }
        ListView {
            id: messageListModel
            model: messageListModelList

            delegate: Text {
                text: display
                textFormat: Text.StyledText
            }

            Timer {
                objectName: "clearOldMessagesTimer"

                interval: 1000
                running: true
                repeat: true
            }

            Layout.fillWidth: true
            Layout.minimumHeight: contentHeight
        }
    }
}
