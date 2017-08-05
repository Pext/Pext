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

ScrollView {
    Layout.fillHeight: true
    Layout.fillWidth: true

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
        visible: resultList.hasEntries == false
        anchors.centerIn: parent
    }

    ListView {
        visible: resultList.hasEntries == true
        anchors.topMargin: headerText.text ? headerText.height : 0
        clip: true
        id: resultList
        objectName: "resultListModel"

        signal entryClicked()

        property int maximumIndex: resultListModelMaxIndex
        property bool commandMode: resultListModelCommandMode
        property bool hasEntries: resultListModelHasEntries
        property int depth: resultListModelDepth

        model: resultListModel

        SystemPalette { id: palette; colorGroup: SystemPalette.Active }

        delegate: Component {
            Item {
                property variant itemData: model.modelData
                width: parent.width
                height: text.height
                Column {
                    Text {
                        id: text
                        text: display
                        textFormat: Text.PlainText
                        font.pointSize: 12
                        font.italic:
                            if (!resultListModelCommandMode) {
                                index > resultListModelMaxIndex
                            } else {
                                index == 0
                            }
                        font.bold: resultListModelCommandMode && index == 0
                        color: resultListModelCommandMode ? palette.text : resultList.currentIndex === index ? palette.highlightedText : palette.text
                        Behavior on color { PropertyAnimation {} }
                    }
                }
                MouseArea {
                    enabled: !resultListModelCommandMode
                    anchors.fill: parent

                    hoverEnabled: true

                    onPositionChanged: {
                        resultList.currentIndex = index
                    }
                    onClicked: {
                        resultList.entryClicked()
                    }
                }
            }
        }

        highlight: Rectangle {
            visible: !resultListModelCommandMode
            color: palette.highlight
        }

        highlightMoveDuration: 250
    }
}
