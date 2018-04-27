#!/bin/bash

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

# Fix py2app's site.py (https://bitbucket.org/ronaldoussoren/py2app/issues/195/sitepy-conflict)
mv "$RESOURCEDIR/site.pyc" "$RESOURCEDIR/site_mac.pyc"
cp $(python3 -c "import site; print(site.__file__)") "$RESOURCEDIR/"
cp $(python3 -c "import _sitebuiltins; print(_sitebuiltins.__file__)") "$RESOURCEDIR/"
sed -i.bak 's/site/site_mac/g' "$RESOURCEDIR/__boot__.py"
rm "$RESOURCEDIR/__boot__.py.bak"
{ echo -e 'import sys,os\nsys.path.append(os.environ["RESOURCEPATH"])'; cat "$RESOURCEDIR/__boot__.py"; } >boot.new
mv "boot.new" "$RESOURCEDIR/__boot__.py"
