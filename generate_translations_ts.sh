#!/bin/sh

# lupdate-qt5 does not support Python and pylupdate5 does not support QML
pylupdate5 pext/__main__.py -ts pext/i18n/pext.dummy.py.ts
lupdate-qt5 pext/qml/* -ts pext/i18n/pext.dummy.qml.ts

# Sed fixes for pylupdate5's broken behaviour
sed -i 's#<location filename="__main__.py"#<location filename="../__main__.py"#g' pext/i18n/pext.dummy.py.ts

# Merge both together in a new dummy file
lconvert -i pext/i18n/pext.dummy.py.ts pext/i18n/pext.dummy.qml.ts -o pext/i18n/pext.dummy.ts

# Remove tmp files
rm -f pext/i18n/pext.dummy.py.ts pext/i18n/pext.dummy.qml.ts
