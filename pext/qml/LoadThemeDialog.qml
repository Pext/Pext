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

    property var themes
    property var loadRequest

    property url themesPath

    ColumnLayout {
        id: columnLayout
        width: parent.width

        anchors.fill: parent

        Label {
            text: qsTr("Choose the theme to switch to:")
        }

        ComboBox {
            id: combobox
            model: themes
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("Note: You must restart Pext to apply the new theme.")
        }
    }

    Component.onCompleted: {
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        loadRequest(combobox.currentText)
    }
}

