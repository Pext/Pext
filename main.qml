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

import QtQuick 2.2
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.2
import QtQuick.Window 2.1

ApplicationWindow {
    id: applicationWindow
    title: 'PyPass'
    property int margin: 10
    width: Screen.width
    height: 185

    flags: Qt.FramelessWindowHint | Qt.Window

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: margin
        RowLayout {
            Layout.fillWidth: true
            TextField {
                objectName: "searchInput"

                font.pixelSize: 24
                focus: true

                Layout.fillWidth: true
            }
        }
        ScrollView {
            Layout.fillHeight: true
            Layout.fillWidth: true

            ListView {
                objectName: "resultList"

                model: listViewModel
                delegate: Text { 
                    text: display
                    font.pixelSize: 18
                }

                Layout.fillHeight: true
                Layout.fillWidth: true
            }
        }
    }
}
