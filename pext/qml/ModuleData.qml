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
        height: headerText.text ? 23 : 0
        Text {
            id: headerText
            objectName: "headerText"

            textFormat: Text.PlainText
            font.pixelSize: 18
        }
    }

    BusyIndicator {
        visible: resultList.hasEntries == false
        anchors.centerIn: parent
    }

    ListView {
        visible: resultList.hasEntries == true
        anchors.topMargin: headerText.text ? 23 : 0
        clip: true
        id: resultList
        objectName: "resultListModel"

        signal entryClicked()

        property int maximumIndex: resultListModelMaxIndex
        property bool commandMode: resultListModelCommandMode
        property bool hasEntries: resultListModelHasEntries

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
                        font.italic:
                            if (!resultListModelCommandMode) {
                                index > resultListModelMaxIndex
                            } else {
                                index == 0
                            }
                        color: resultList.currentIndex === index ? "red" : "steelblue"
                        Behavior on color { PropertyAnimation {} }
                    }
                }
                MouseArea {
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
    }
}
