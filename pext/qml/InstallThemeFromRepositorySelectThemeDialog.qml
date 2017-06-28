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
    property var installRequest

    ColumnLayout {
        Label {
            text: qsTr("Choose the theme to install:")
        }

        ComboBox {
            id: combobox
            model: themes.map(function(theme) { return theme.name; })
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("Choose the preferred download source:")
        }

        ComboBox {
            id: urlSelectionBox
            model: themes[combobox.currentIndex].git_urls
            Layout.fillWidth: true
        }

        Label {
            text: qsTr("Theme information:")
        }

        Label {
            text: qsTr("Developer: ") + themes[combobox.currentIndex].developer
        }

        Label {
            text: qsTr("Description: ") + themes[combobox.currentIndex].description
        }

        Label {
            text: qsTr("License: ") + themes[combobox.currentIndex].license
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

