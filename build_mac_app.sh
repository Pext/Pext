#/bin/sh

# Run py2app
python3 setup.py py2app

# Copy additional files py2app doesn't copy for some reason
RESOURCEDIR="dist/Pext.app/Contents/Resources"
cp "pext/VERSION" "$RESOURCEDIR"
cp "pext/git_describe.py" "$RESOURCEDIR"
cp -r "pext/i18n" "$RESOURCEDIR/i18n"
cp -r "pext/images" "$RESOURCEDIR/images"
cp -r "pext/qml" "$RESOURCEDIR/qml"
cp -r "pext/helpers" "$RESOURCEDIR/helpers"
