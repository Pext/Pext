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

Item {
    id: contentRow
    height: parent.height

    GridLayout {
        id: moduleDataGrid
        anchors.fill: parent
        rowSpacing: 0
        columnSpacing: 0
        flow: parent.width > parent.height ? GridLayout.LeftToRight : GridLayout.TopToBottom

        ScrollView {
            id: contextMenuContainer
            visible: contextMenuVisible

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.width / 4
            Layout.minimumHeight: moduleDataGrid.height / 4
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? moduleDataGrid.width / 4 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? moduleDataGrid.height / 4 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1

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
                                color: contextMenu.currentIndex === index ? palette.highlightedText : palette.text
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

        Rectangle {
            color: palette.window
            visible: contextMenuContainer.visible

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.minimumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1
        }

        ScrollView {
            id: mainContent

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.width / 4
            Layout.minimumHeight: moduleDataGrid.height / 4
            Layout.rowSpan: 1
            Layout.columnSpan: 1


            Item {
                width: parent.width
                visible: headerText.text
                Column {
                    Text {
                        id: headerText
                        color: palette.highlight
                        objectName: "headerText"
                        font.pointSize: 12

                        textFormat: Text.PlainText
                    }
                }
                MouseArea {
                    anchors.fill: headerText.parent
                    acceptedButtons: Qt.RightButton

                    onClicked: {
                        resultList.openBaseMenu();
                    }
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
                signal openBaseMenu()

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
                                color: {
                                    if (resultList.currentIndex == index) {
                                        if (contextMenu.visible) {
                                            return inactivePalette.highlightedText;
                                        } else {
                                            return palette.highlightedText;
                                        }
                                    } else {
                                        if (contextMenu.visible) {
                                            return inactivePalette.text;
                                        } else {
                                            return palette.text;
                                        }
                                    }
                                }
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

        Rectangle {
            color: palette.window
            visible: contextInfoPanel.text

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.minimumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1
        }

        ScrollView {
            visible: contextInfoPanel.text

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.width / 4
            Layout.minimumHeight: moduleDataGrid.height / 4
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? moduleDataGrid.width / 4 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? moduleDataGrid.height / 4 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1

            horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

            Text {
                id: contextInfoPanel
                objectName: "contextInfoPanel"
                text: ""
                wrapMode: Text.Wrap
                width: contentRow.width - mainContent.width
                color: palette.text

                onLinkActivated: Qt.openUrlExternally(link)
            }
        }

        Rectangle {
            color: palette.base
            visible: baseInfoPanel.text

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.minimumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? 5 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? 5 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1
        }

        ScrollView {
            visible: baseInfoPanel.text

            Layout.fillHeight: true
            Layout.fillWidth: true
            Layout.minimumWidth: moduleDataGrid.width / 4
            Layout.minimumHeight: moduleDataGrid.height / 4
            Layout.maximumWidth: moduleDataGrid.flow == GridLayout.LeftToRight ? moduleDataGrid.width / 4 : moduleDataGrid.width
            Layout.maximumHeight: moduleDataGrid.flow == GridLayout.TopToBottom ? moduleDataGrid.height / 4 : moduleDataGrid.height
            Layout.rowSpan: 1
            Layout.columnSpan: 1

            horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

            Text {
                id: baseInfoPanel
                objectName: "baseInfoPanel"
                text: ""
                wrapMode: Text.Wrap
                width: contentRow.width - mainContent.width
                color: palette.highlight

                onLinkActivated: Qt.openUrlExternally(link)
            }
        }
    }
}
