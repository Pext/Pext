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
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0

Row {
    id: contentRow
    height: parent.height

    ScrollView {
        id: contextMenuContainer
        width: contentRow.width / 4
        height: contentRow.height
        visible: contextMenuVisible

        onVisibleChanged: contextMenu.currentIndex = 0;

        property bool contextMenuVisible: contextMenuEnabled

        ListView {
            clip: true
            id: contextMenu
            objectName: "contextMenuModel"

            signal entryClicked()
            signal closeContextMenu()

            model: contextMenuModel

            delegate: Component {
                Item {
                    property variant itemData: model.modelData
                    width: parent.width
                    height: text.height
                    Column {
                        Text {
                            id: text
                            objectName: "text"
                            text: display
                            textFormat: Text.PlainText
                            font.pointSize: 12
                            color: contextMenu.isCurrentIndex ? palette.highlightedText : palette.text
                            Behavior on color { PropertyAnimation {} }
                        }
                    }
                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton | Qt.RightButton

                        hoverEnabled: true

                        onPositionChanged: {
                            contextMenu.currentIndex = index
                        }
                        onClicked: {
                            if (mouse.button == Qt.LeftButton) {
                                contextMenu.entryClicked();
                            } else {
                                contextMenu.closeContextMenu();
                            }
                        }
                    }
                }
            }
            highlight: Rectangle {
                color: palette.highlight
            }

            highlightMoveDuration: 250
        }
    }

    ScrollView {
        id: mainContent
        width: contentRow.width / 4 * (4 - (infoPanel.visible ? 1 : 0) - (contextMenuContainer.visible ? 1 : 0))
        height: contentRow.height

        Behavior on width { PropertyAnimation {} }

        Item {
            width: parent.width
            visible: headerText.text
            Text {
                id: headerText
                color: palette.mid
                objectName: "headerText"
                font.pointSize: 12

                textFormat: Text.PlainText
            }
        }

        BusyIndicator {
            visible: !resultList.hasEntries
            anchors.centerIn: parent
        }

        ListView {
            visible: resultList.hasEntries
            anchors.topMargin: headerText.text ? headerText.height : 0
            clip: true
            id: resultList
            objectName: "resultListModel"

            signal entryClicked()
            signal openContextMenu()

            property int normalEntries: resultListModelNormalEntries
            property int commandEntries: resultListModelCommandEntries
            property bool commandMode: resultListModelCommandMode
            property bool hasEntries: resultListModelHasEntries
            property int depth: resultListModelDepth

            model: resultListModel

            SystemPalette { id: palette; colorGroup: SystemPalette.Active }
            SystemPalette { id: inactivePalette; colorGroup: SystemPalette.Inactive }

            delegate: Component {
                Item {
                    property variant itemData: model.modelData
                    width: parent.width
                    height: text.height
                    Column {
                        Text {
                            id: text
                            objectName: "text"
                            text: display
                            textFormat: Text.PlainText
                            font.pointSize: 12
                            font.italic:
                                if (!resultListModelCommandMode) {
                                    index >= resultListModelNormalEntries
                                } else {
                                    index < resultListModelCommandEntries
                                }
                            color: resultListModelCommandMode ? (contextMenuContainer.visible ? inactivePalette.text : palette.text) : resultList.isCurrentIndex ? (contextMenuContainer.visible ? inactivePalette.highlightedText : palette.highlightedText) : (contextMenuContainer.visible ? inactivePalette.text : palette.text)
                            Behavior on color { PropertyAnimation {} }
                        }
                    }
                    MouseArea {
                        enabled: !contextMenuContainer.visible
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton | Qt.RightButton

                        hoverEnabled: true

                        onPositionChanged: {
                            resultList.currentIndex = index
                        }
                        onClicked: {
                            if (mouse.button == Qt.LeftButton) {
                                resultList.entryClicked();
                            } else {
                                resultList.openContextMenu();
                            }
                        }
                    }
                }
            }
            highlight: Rectangle {
                color: contextMenuContainer.visible ? inactivePalette.highlight : palette.highlight
            }

            highlightMoveDuration: 250
        }
    }

    ScrollView {
        width: contentRow.width - mainContent.width
        height: contentRow.height
        visible: infoPanel.text
        horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

        Text {
            id: infoPanel 
            objectName: "infoPanel"
            text: ""
            wrapMode: Text.Wrap
            width: contentRow.width - mainContent.width

            onLinkActivated: Qt.openUrlExternally(link)
        }
    }
}
