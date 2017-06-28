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

    property var installRequest

    ColumnLayout {
        Label {
            text: qsTr("Enter the git URL of the theme to install:")
        }

        TextField {
            id: textfield
            Layout.fillWidth: true
        }
    }

    Component.onCompleted: {
        visible = true;
        textfield.focus = true;
    }

    onAccepted: {
        installRequest(textfield.text);
    }
}

