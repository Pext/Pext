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
    title: qsTr("Load profile")
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    property var currentProfile
    property var profiles
    property var loadRequest

    ColumnLayout {
        id: columnLayout
        width: parent.width

        anchors.fill: parent

        Label {
            text: qsTr("Choose the profile to switch to:")
        }

        ComboBox {
            id: combobox
            model: profiles
            Layout.fillWidth: true
        }

        CheckBox {
            id: newInstance
            text: qsTr("Open in a new window")
        }

        Label {
            opacity: newInstance.checked ? 0 : 1
            text: qsTr("Note: Pext will restart to switch profile.")
        }
    }

    Component.onCompleted: {
        combobox.currentIndex = profiles.indexOf(currentProfile);
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        loadRequest(combobox.currentText, newInstance.checked);
        destroy();
    }

    onRejected: destroy();
}
