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
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    property var modules
    property var loadRequest

    property url modulesPath
    property var moduleSettings: []
    property var moduleChosenSettings: {}

    ColumnLayout {
        width: parent.width

        anchors.fill: parent

        Label {
            text: qsTr("Choose the module to load:")
        }

        ComboBox {
            id: combobox
            model: modules
            Layout.fillWidth: true
            onCurrentIndexChanged: getModuleSettings();
        }

        ScrollView {
            width: parent.width

            anchors.left: parent.left
            anchors.right: parent.right

            ListView {
                id: settingsList

                width: parent.width
                model: moduleSettings

                spacing: 5

                delegate: Column {
                    id: root
                    width: parent.width

                    Label {
                        text: modelData.description
                        width: root.width
                        wrapMode: Text.Wrap
                    }

                    TextField {
                        placeholderText: modelData.default ? modelData.default : ""
                        width: root.width
                        onEditingFinished: moduleChosenSettings[modelData.name] = text
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        getModuleSettings();
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        combobox.focus = true; // Ensure onEditingFinish gets called of the textfield
        var settingString = "";
        for (var key in moduleChosenSettings)
            settingString += key + "=" + moduleChosenSettings[key] + " ";

        loadRequest(combobox.currentText, settingString)
    }

    function getData(url, callback) {
        var xmlhttp = new XMLHttpRequest();

        xmlhttp.onreadystatechange = function() {
            if (xmlhttp.readyState == XMLHttpRequest.DONE && xmlhttp.status == 200) {
                callback(xmlhttp.response);
            }
        }

        xmlhttp.open("GET", url, true);
        xmlhttp.send();
    }

    function getModuleSettings() {
        // Reset
        moduleSettings = []
        moduleChosenSettings = {}

        var path = modulesPath + "/pext_module_" + combobox.currentText + "/metadata.json";
        getData(path, function(response) {
            moduleSettings = JSON.parse(response)["settings"];
        });
    }
}

