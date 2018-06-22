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
import QtQuick.Controls 1.4
import QtQuick.Dialogs 1.2

Dialog {
    title: qsTr("About Pext")
    standardButtons: StandardButton.Ok

    height: 350
    width: 500

    property var translators: {"en": [{"name": "Sylvia van Os", "email": "sylvia@hackerchick.me"}],
                               "es": [{"name": "Rose Garcia", "email": "rosegarcia@protonmail.com"},
                                      {"name": "Emily Lau", "email": "fuchslein@hackerchick.me"}],
                               "fr": [{"name": "Aurora Yeen"}],
                               "nb_NO": [{"name": "Allan Nordhøy", "email": "epost@anotheragency.no"}],
                               "hu": [{"name": "Szöllősi Attila", "email": "ata2001@airmail.cc"}],
                               "hi": [{"name": "Satyam Singh", "email": "trueleo@protonmail.com"}],
                               "nl": [{"name": "Sylvia van Os", "email": "sylvia@hackerchick.me"},
                                      {"name": "Heimen Stoffels", "email": "vistausss@outlook.com"}],
                               "pl": [{"name": "Konrad Dybcio"}],
                               "ru": [{"name": "Ivan Semkin", "email": "ivan@semkin.ru"}],
                               "zh_Hant": [{"name": "Jeff Huang", "email": "s8321414@gmail.com"}]}

    TabView {
        width: parent.width
        height: parent.height

        SystemPalette { id: palette; colorGroup: SystemPalette.Active }

        Tab {
            title: qsTr("Copyright")
            ScrollView {
                Item {
                    height: childrenRect.height
                    width: parent.parent.width

                    Image {
                        asynchronous: true
                        source: "../images/scalable/logo.svg"
                        fillMode: Image.Pad
                        height: 150
                    }

                    Text {
                        y: 150
                        color: palette.text
                        width: parent.parent.width
                        wrapMode: Text.Wrap
                        text:
                            "<h1>Pext " + version + "</h1><br>" +
                            "Copyright 2015 - 2018 Sylvia van Os &lt;<a href='mailto:sylvia@hackerchick.me'>sylvia@hackerchick.me</a>&gt;<br><br>" +
                            "This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.<br><br>" +
                            "This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.<br><br>" +
                            "You should have received a copy of the GNU General Public License along with this program. If not, see <a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses/</a>."

                        onLinkActivated: Qt.openUrlExternally(link)
                    }
                }
            }
        }

        Tab {
            title: qsTr("Translators")
            ScrollView {
                Text {
                    color: palette.text
                    width: parent.parent.width
                    wrapMode: Text.Wrap
                    text: "<a href='https://hosted.weblate.org/engage/pext/'>"
                          + qsTr("Want to help translate Pext? Please click here.")
                          + "</a><br><h3>" + qsTr("The Pext team would like to thank the following users for translating Pext:")
                          + "</h3><br>";
    
                    Component.onCompleted: {
                          for (var lang in translators) {
                              text += "<b>" + Object.keys(locales).filter(function(key) { return locales[key] === lang })[0] + "</b><br>";
                              for (var translatorData in translators[lang]) {
                                  text += translators[lang][translatorData]["name"]
                                  if (translators[lang][translatorData]["email"]) {
                                      text += " &lt;<a href='mailto:" + translators[lang][translatorData]["email"] + "'>" + translators[lang][translatorData]["email"] + "</a>&gt;";
                                  }
                                  text += "<br>";
                              }
                              text += "<br>";
                          }
                    }

                    onLinkActivated: Qt.openUrlExternally(link)
                }
            }
        }
    }

    Component.onCompleted: visible = true;
}

