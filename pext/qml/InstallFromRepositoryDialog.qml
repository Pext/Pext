/*
    Copyright (c) 2016 - 2018 Sylvia van Os <sylvia@hackerchick.me>

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
    title: type == "modules" ? qsTr("Module Installation") : qsTr("Theme Installation")
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    height: 350
    width: type == "modules" ? 600 : 300

    property var type
    property var installedObjects
    property var installRequest
    property var repositories
    property var expectedVersion: 2
    property var currentRepoVersion: 2
    property var objects: []

    ColumnLayout {
        Label {
            text: type == "modules" ? qsTr("Module source:") : qsTr("Theme source:")
        }

        ComboBox {
            id: combobox
            model: repositories.map(function(repository) { return repository.name; })
            onCurrentIndexChanged: getObjects(combobox.currentIndex)
            Layout.fillWidth: true
        }

        Label {
            text: type == "modules" ? qsTr("No modules available from this source.") : qsTr("No themes available from this source.")
            font.bold: true
            visible: objects.length == 0
        }

        Label {
            text: qsTr("Repository format not supported (expected version %1, got version %2).").arg(expectedVersion).arg(currentRepoVersion)
            font.bold: true
            visible: expectedVersion != currentRepoVersion
        }

        Label {
            text: qsTr("Module:")
            visible: objects.length >= 1
        }

        ComboBox {
            id: objectComboBox
            model: objects.map(function(obj) { return obj.name; })
            Layout.fillWidth: true
            visible: objects.length >= 1
        }

        Label {
            text: qsTr("Download source:")
            visible: objects.length >= 1
        }

        ComboBox {
            id: urlSelectionBox
            model: objects[objectComboBox.currentIndex] ? objects[objectComboBox.currentIndex].git_urls : [""]
            Layout.fillWidth: true
            visible: objects.length >= 1
        }

        Label {
            text: type == "modules" ? qsTr("This module is already installed.") : qsTr("This theme is already installed.")
            font.bold: true
            visible: objects.length >= 1 && Object.keys(installedObjects).indexOf(objects[objectComboBox.currentIndex].id) != -1
        }

        Label {
            text: qsTr("This module does not seem to support %1.").arg(platform)
            font.bold: true
            visible: type == "modules" && objects.length >= 1 && (objects[objectComboBox.currentIndex].platforms == null || objects[objectComboBox.currentIndex].platforms.indexOf(platform) == -1)
        }

        Label {
            text: qsTr("Details:")
            font.bold: true
            visible: objects.length >= 1
        }

        Label {
            text: objects[objectComboBox.currentIndex] ? qsTr("Creator: ") + objects[objectComboBox.currentIndex].developer : ""
            visible: objects.length >= 1
        }

        Label {
            text: objects[objectComboBox.currentIndex] ? qsTr("Description: ") + objects[objectComboBox.currentIndex].description : ""
            visible: objects.length >= 1
        }

        Label {
            text: objects[objectComboBox.currentIndex] ? qsTr("License: ") + objects[objectComboBox.currentIndex].license : ""
            visible: objects.length >= 1
        }

        Label {
            text: qsTr("As Pext modules are code, please make sure you trust the developer before continuing.")
            font.bold: true
            visible: objects.length >= 1 && type == "modules"
        }
    }

    Component.onCompleted: {
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        if (urlSelectionBox.currentText && objects[objectComboBox.currentIndex].id) {
            installRequest(urlSelectionBox.currentText, objects[objectComboBox.currentIndex].id);
        }
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

    function getObjects(repoIndex) {
        modules = [];
        getData(repositories[repoIndex].url, function(response) {
            var jsonResponse = JSON.parse(response)

            if (jsonResponse.version != 2) {
                currentRepoVersion = jsonResponse.version;
                return;
            }

            var objectList = jsonResponse[type];

            if (objectList.length == 0) {
                objects = [];
                return;
            }

            // Get object data
            var objectsData = [];

            for (var i = 0; i < objectList.length; i++) {
                getData(objectList[i], function(response) {
                    objectsData.push(JSON.parse(response));
                    if (objectsData.length === objectList.length) {
                         objects = objectsData.sort(function(a, b) { return a.name.localeCompare(b.name); } );
                    };
                });
            };
        });
    }
}

