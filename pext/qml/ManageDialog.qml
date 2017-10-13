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

import QtQuick 2.3
import QtQuick.Controls 1.2
import QtQuick.Dialogs 1.2
import QtQuick.Layouts 1.0

Dialog {
    title: "Pext"
    standardButtons: StandardButton.Ok

    property var manageableObjects
    property var updateRequest
    property var uninstallRequest

    height: 250
    width: 400

    ScrollView {
        width: parent.width

        anchors.fill: parent

        ListView {
            anchors.fill: parent
            model: Object.keys(manageableObjects)

            width: parent.width

            spacing: 20
    
            delegate: Column {
                id: root
                width: parent.width

    			Label {
                    text: manageableObjects[modelData].metadata.name + "\n"
                    wrapMode: Text.Wrap 
                    font.bold: true
                }

                Label {
                    visible: manageableObjects[modelData].metadata.version !== undefined && manageableObjects[modelData].metadata.last_updated !== undefined

                    text: qsTr("Version: %1 (%2)").arg(manageableObjects[modelData].metadata.version).arg(manageableObjects[modelData].metadata.last_updated)
                    width: root.width
                    wrapMode: Text.Wrap
                }
    
                Label {
                    visible: manageableObjects[modelData].metadata.developer !== undefined

                    text: qsTr("Developer: %1").arg(manageableObjects[modelData].metadata.developer)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
    
                Label {
                    visible: manageableObjects[modelData].metadata.description !== undefined

                    text: qsTr("Description: %1").arg(manageableObjects[modelData].metadata.description)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
        
                Label {
                    visible: manageableObjects[modelData].metadata.license !== undefined

                    text: qsTr("License: %1").arg(manageableObjects[modelData].metadata.license)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
        
                Label {
                    visible: manageableObjects[modelData].metadata.homepage !== undefined

                    text: qsTr("Homepage: %1").arg("<a href='" + manageableObjects[modelData].metadata.homepage + "'>" + manageableObjects[modelData].metadata.homepage + "</a>")
                    textFormat: Text.RichText
                    width: root.width
                    wrapMode: Text.Wrap 

                    onLinkActivated: Qt.openUrlExternally(link)

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }
                }
                
                Label {
                    visible: manageableObjects[modelData].source !== undefined

                    text: qsTr("Download source: %1").arg("<a href='" + manageableObjects[modelData].source + "'>" + manageableObjects[modelData].source + "</a>")
                    textFormat: Text.RichText
                    width: root.width
                    wrapMode: Text.Wrap 

                    onLinkActivated: Qt.openUrlExternally(link)

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                    }
                }
    
                GridLayout {
                    Button {
                        visible: manageableObjects[modelData].source !== undefined

                        text: qsTr("Update")
                        onClicked: {
                            updateRequest(modelData)
                            close()
                        }
                    }
                    
                    Button {
                        visible: manageableObjects[modelData].source !== undefined

                        text: qsTr("Uninstall")
                        onClicked: {
                            uninstallRequest(modelData)
                            close()
                        }
                    }
                }
            }
        }
    }

    Component.onCompleted: visible = true;
}

