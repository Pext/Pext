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

    property var modules
    property var updateRequest
    property var uninstallRequest

    height: 250
    width: 400

    ScrollView {
        width: parent.width

        anchors.fill: parent

        ListView {
            anchors.fill: parent
            model: Object.keys(modules)

            width: parent.width

            spacing: 20
    
            delegate: Column {
                id: root
                width: parent.width

    			Label {
                    text: modules[modelData].metadata.name + "\n"
                    wrapMode: Text.Wrap 
                    font.bold: true
                }
    
                Label {
                    text: qsTr("Developer: %1").arg(modules[modelData].metadata.developer)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
    
                Label {
                    text: qsTr("Description: %1").arg(modules[modelData].metadata.description)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
        
                Label {
                    text: qsTr("License: %1").arg(modules[modelData].metadata.license)
                    width: root.width
                    wrapMode: Text.Wrap 
                }
        
                Label {
                    text: qsTr("Homepage: %1").arg("<a href='" + modules[modelData].metadata.homepage + "'>" + modules[modelData].metadata.homepage + "</a>")
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
                    text: qsTr("Download source: %1").arg("<a href='" + modules[modelData].source + "'>" + modules[modelData].source + "</a>")
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
                        text: qsTr("Update")
                        onClicked: {
                            updateRequest(modelData)
                            close()
                        }
                    }
                    
                    Button {
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

