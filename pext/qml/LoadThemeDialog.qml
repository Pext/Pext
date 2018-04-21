/*
    Copyright (c) 2015 - 2018 Sylvia van Os <sylvia@hackerchick.me>

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
    title: qsTr("Switch theme")
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    property var currentTheme
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
            model: [qsTr("No theme")].concat(Object.keys(themes).map(function(theme) { return themes[theme].metadata.name }))
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("Note: Pext will restart to apply the new theme.")
        }
    }

    Component.onCompleted: {
        if (currentTheme === null) {
            combobox.currentIndex = 0;
        } else {
            combobox.currentIndex = Object.keys(themes).indexOf(currentTheme) + 1;
        }
        visible = true;
        combobox.focus = true;
    }

    onAccepted: {
        if (combobox.currentIndex == 0) {
            loadRequest(null);
        } else {
            loadRequest(themes[Object.keys(themes)[combobox.currentIndex - 1]].metadata.id);
        }
    }
}

