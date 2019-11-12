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
    title: moduleName.length == 0 ? qsTr("Pext") : qsTr("Pext - %1").arg(moduleName)
    standardButtons: StandardButton.Ok | StandardButton.Cancel

    property var moduleName
    property var description
    property var isPassword
    property var isMultiline
    property var prefill
    property var requestAccepted
    property var requestRejected

    Column {
        id: root
        width: parent.width

        Label {
            text: description
            width: root.width
            wrapMode: Text.Wrap
        }

        TextField {
            visible: !isMultiline
            id: userInput
            echoMode: isPassword ? TextInput.Password : TextInput.Normal
            placeholderText: prefill
            width: root.width
        }

        TextArea {
            visible: isMultiline
            id: userInputMultiline
            text: prefill
            width: root.width
        }
    }

    Component.onCompleted: {
        visible = true;
        if (isMultiline) {
            userInputMultiline.focus = true;
        } else {
            userInput.focus = true;
        }
    }

    onAccepted: {
        if (isMultiline) {
            requestAccepted(userInputMultiline.text);
        } else {
            requestAccepted(userInput.text);
        }
        destroy();
    }

    onRejected: {
        requestRejected();
        destroy();
    }
}
