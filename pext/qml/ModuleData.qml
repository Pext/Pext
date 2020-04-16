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

import "repeat_polyfill.js" as RepeatPolyfill

import QtQuick 2.6
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.0
import QtQuick.Window 2.0

Item {
    id: contentRow
    height: parent.height

    property var disableReason: 0
    property var progressStates: []

    Shortcut {
        id: enterShortcut
        enabled: false
        sequence: "Return"
    }

    Shortcut {
        id: argsShortcut
        enabled: false
        sequence: "Ctrl+Return"
    }

    GridLayout {
        visible: !contentRow.disableReason
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
                signal selectExplicitNoMinimize()
                signal openArgumentsInput()
                signal closeContextMenu()

                model: contextMenuModelFull

                property int entrySpecificCount: contextMenuModelEntrySpecificCount

                delegate: Component {
                    Item {
                        property variant itemData: model.modelData
                        width: parent.width
                        height: column.height
                        Column {
                            id: column
                            topPadding: (index >= (contextMenu.entrySpecificCount)) ? 10 : undefined
                            height: text.height
                            Text {
                                id: text
                                objectName: "text"
                                text: display
                                textFormat: Text.PlainText
                                color: contextMenu.currentIndex === index ? palette.highlightedText : palette.text
                                Behavior on color { PropertyAnimation {} }
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton | Qt.MidButton | Qt.RightButton

                            hoverEnabled: true

                            onPositionChanged: {
                                contextMenu.currentIndex = index
                            }
                            onClicked: {
                                if (mouse.button == Qt.LeftButton) {
                                    contextMenu.entryClicked();
                                } else if (mouse.button == Qt.MidButton) {
                                    resultList.selectExplicitNoMinimize();
                                } else {
                                    contextMenu.closeContextMenu();
                                }
                            }
                        }
                    }
                }
                highlight: Rectangle {
                    transform: Translate { y: ((contextMenu.currentIndex >= (contextMenu.entrySpecificCount)) ? 10 : 0) }
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
                visible: headerText.text || treeText.text

                Column {
                    id: headerHolder
                    objectName: "headerHolder"

                    Text {
                        id: headerText
                        objectName: "headerText"

                        color: palette.highlight
                        textFormat: Text.PlainText
                    }
                    Text {
                        id: treeText
                        objectName: "treeText"

                        text: {
                            var text = "";
                            for (var i = 0; i < resultList.tree.length; i++) {
                                if (headerText.text) {
                                    text += "  ";
                                }
                                for (var j = 0; j < i; j++) {
                                    text += "  ";
                                }
                                var value_text = ""
                                if (resultList.tree[i]['value']) {
                                    value_text = resultList.tree[i]['value'] + " "
                                }
                                if (resultList.tree[i]['context_option']) {
                                    value_text += "(" + resultList.tree[i]['context_option'] + ")"
                                }
                                text += value_text;
                                if (i < resultList.tree.length - 1) {
                                    text += "\n";
                                }
                            }
                            return text;
                        }
                        color: palette.highlight
                        textFormat: Text.PlainText
                    }
                }
            }

            BusyIndicator {
                visible: !resultList.hasEntries && searchInputFieldEmpty
                anchors.centerIn: parent
            }

            TextEdit {
                visible: resultList.hasEntries && resultList.normalEntries == 0 && resultList.commandEntries == 0 && !searchInputFieldEmpty

                text: "<h2>" + qsTr("No results") + "</h2>" +
                      (resultList.unprocessedQueueCount > 0 ? ("<p>" + qsTr("Still processing %1 module request(s)…".arg(resultList.unprocessedQueueCount), "", resultList.unprocessedQueueCount) + "</p>") : "")

                anchors.centerIn: parent
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

            ListView {
                visible: resultList.hasEntries
                anchors.topMargin: headerHolder.height
                clip: true
                id: resultList
                objectName: "resultListModel"

                signal entryClicked()
                signal selectExplicitNoMinimize()
                signal openContextMenu()
                signal openArgumentsInput()

                signal sortModeChanged()
                property var pextSortMode: sortMode

                property int normalEntries: resultListModelNormalEntries
                property int commandEntries: resultListModelCommandEntries
                property bool hasEntries: resultListModelHasEntries
                property variant tree: resultListModelTree
                property int unprocessedQueueCount: unprocessedCount

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
                                width: parent.parent.width
                                objectName: "text"
                                text: {
                                    var line = "<table width=" + parent.width + "><tr><td><span>" + (index >= resultListModelNormalEntries ? "<i>" : "") + "&nbsp;".repeat((resultList.tree.length + (headerText.text ? 1 : 0)) * 2) + String(display).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + (index >= resultListModelNormalEntries ? "</i>" : "") + "</td><td align='right'><code>";
                                    if (resultList.currentIndex === index) {
                                        line += (resultList.currentIndex < resultListModelNormalEntries ? enterShortcut.nativeText : argsShortcut.nativeText);
                                    } else if (resultList.currentIndex < resultListModelNormalEntries && resultListModelNormalEntries === index) {
                                        line += argsShortcut.nativeText;
                                    }
                                    return line + "</code></td></tr></table>"
                                }
                                textFormat: Text.RichText
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
                            acceptedButtons: Qt.LeftButton | Qt.MidButton | Qt.RightButton

                            hoverEnabled: true

                            onPositionChanged: {
                                resultList.currentIndex = index
                            }
                            onClicked: {
                                if (mouse.button == Qt.LeftButton) {
                                    resultList.entryClicked();
                                } else if (mouse.button == Qt.MidButton) {
                                    resultList.selectExplicitNoMinimize();
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

    TextEdit {
        objectName: "disabledScreen"
        visible: contentRow.disableReason

        text: {
            var reason = "";
            switch (contentRow.disableReason) {
                case 1:
                    reason = qsTr("Module crashed.");
                    break;
                case 2:
                    reason = qsTr("Updating module…");
                    break;
            }
            var text = "<h2>" + reason + "</h2>";
            for (var i = 0; i < contentRow.progressStates.length; i++) {
                text += "<pre>" + contentRow.progressStates[i] + "</pre>";
            }
            return text;
        }

        color: palette.text
        textFormat: TextEdit.RichText
        readOnly: true
        selectByMouse: true
        wrapMode: TextEdit.Wrap
        horizontalAlignment: TextEdit.AlignHCenter
        verticalAlignment: TextEdit.AlignVCenter
        Layout.fillWidth: true
        padding: 10
    }
}
