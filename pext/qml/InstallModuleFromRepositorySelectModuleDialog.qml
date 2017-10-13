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
    property var installRequest

    ColumnLayout {
        Label {
            text: qsTr("Choose the module to install:")
        }

        ComboBox {
            id: combobox
            model: modules.map(function(module) { return module.name; })
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("Choose the preferred download source:")
        }

        ComboBox {
            id: urlSelectionBox
            model: modules[combobox.currentIndex].git_urls
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("This module does not seem to support %1.").arg(platform)
            font.bold: true
            visible: modules[combobox.currentIndex].platforms == null || modules[combobox.currentIndex].platforms.indexOf(platform) == -1
        }

        Label {
            text: qsTr("Module information:")
        }

        Label {
            text: qsTr("Developer: ") + modules[combobox.currentIndex].developer
        }

        Label {
            text: qsTr("Description: ") + modules[combobox.currentIndex].description
        }

        Label {
            text: qsTr("License: ") + modules[combobox.currentIndex].license
        }

        Label {
            text: qsTr("As Pext modules are code, please make sure you trust the developer before continuing.")
            font.bold: true
        }
    }

    Component.onCompleted: {
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        installRequest(urlSelectionBox.currentText);
    }
}

