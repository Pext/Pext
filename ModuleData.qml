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

ScrollView {
    Layout.fillHeight: true
    Layout.fillWidth: true

    ListView {
        id: resultList
        objectName: "resultListModel"

        property int maximumIndex: resultListModelMaxIndex
        property bool commandMode: resultListModelCommandMode

        model: resultListModel

        preferredHighlightBegin: 0
        preferredHighlightEnd: 0.5*height
        highlightRangeMode: ListView.ApplyRange

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
