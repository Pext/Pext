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

import QtQuick 2.3
import QtQuick.Controls 1.2
import QtQuick.Dialogs 1.2
import QtQuick.Layouts 1.0

Dialog {
    title: qsTr("Manage profiles")
    standardButtons: StandardButton.Ok

    property var profiles
    property var createRequest
    property var renameRequest
    property var removeRequest

    height: 250
    width: 400

    RowLayout {
        id: rowLayout
        width: parent.width

        TextField {
            Layout.fillWidth: true
            id: newProfileName
            placeholderText: qsTr("Enter profile name")
        }

        Button {
            text: qsTr("Create")
            onClicked: {
                createRequest(newProfileName.text)
                close()
            }
        }
    }

    ScrollView {
        y: rowLayout.height
        width: parent.width

        ListView {
            anchors.fill: parent
            model: profiles

            width: parent.width

            spacing: 20

            delegate: Column {
                id: root
                width: parent.width

                Label {
                    text: modelData
                    wrapMode: Text.Wrap
                    font.bold: true
                }

                GridLayout {
                    Button {
                        text: qsTr("Rename")
                        onClicked: {
                            var renameProfileDialog = Qt.createComponent("RenameProfileDialog.qml");
                            renameProfileDialog.createObject(applicationWindow,
                                {"profileName": modelData,
                                 "renameRequest": renameRequest});
                            close()
                        }
                    }
                    Button {
                        text: qsTr("Remove")
                        onClicked: {
                            removeRequest(modelData)
                            close()
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: visible = true;

    onAccepted: destroy();
}
