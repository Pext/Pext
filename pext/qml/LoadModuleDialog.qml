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
    title: qsTr("Load module")
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    property var modules
    property var loadRequest

    property url modulesPath
    property var moduleSettings: []
    property var moduleChosenSettings: {}

    property var menuInstallModule

    ColumnLayout {
        width: parent.width

        anchors.fill: parent

        Label {
            text: qsTr("Choose the module to load:")
        }

        ComboBox {
            id: combobox
            model: Object.keys(modules).map(function(module) { return modules[module].metadata.name })
            Layout.fillWidth: true
            onCurrentIndexChanged: getModuleSettings();
        }

        ScrollView {
            width: parent.width
            Layout.fillWidth: true

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
                        visible: modelData.options === undefined
                        placeholderText: modelData.default ? modelData.default : ""
                        width: root.width
                        onEditingFinished: moduleChosenSettings[modelData.name] = text
                    }

                    ComboBox {
                        id: settingComboBox
                        visible: modelData.options !== undefined
                        model: modelData.options
                        currentIndex: modelData.options !== undefined ? modelData.options.indexOf(modelData.default) : 0
                        width: root.width
                        onCurrentIndexChanged: {
                            if (modelData.options !== undefined) {
                                moduleChosenSettings[modelData.name] = modelData.options[currentIndex];
                            }
                        }
                    }
                }
            }
        }
        Button {
            text: qsTr("Get more modules")
            onClicked: {
                menuInstallModule.trigger();
                reject();
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

        var metadata = modules[Object.keys(modules)[combobox.currentIndex]].metadata
        loadRequest(metadata.id, metadata.name, settingString)

        destroy();
    }

    onRejected: destroy();

    function getModuleSettings() {
        // Reset
        moduleSettings = []
        moduleChosenSettings = {}

        moduleSettings = modules[Object.keys(modules)[combobox.currentIndex]].metadata.settings;
    }
}
