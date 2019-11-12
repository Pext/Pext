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
import QtQuick.Dialogs 1.2

MessageDialog {
    title: qsTr("Pext")
    icon: StandardIcon.Question
    standardButtons: StandardButton.Yes | StandardButton.No

    property var confirmedClose;
    property var platform;

    text: platform == 'Darwin' ? qsTr("You are about to quit Pext.\n\nThis will stop any running module.\n\nAre you sure you want to quit?") : qsTr("You are about to quit Pext.\n\nThis will stop any running module and the global hotkey will not work until you restart Pext manually.\n\nAre you sure you want to quit?")

    Component.onCompleted: {
        visible = true;
    }

    onYes: {
        confirmedClose();
    }

    onNo: destroy();
}
