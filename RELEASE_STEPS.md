**This documentation is for maintainers. If you're an user, please ignore it.**

``<VERSION>`` is the release version (example: 0.1.0)  
``<DATE>`` is the release date as YYYY-MM-DD (example: 2015-12-22)

# When releasing, do the following:
## i18n
1. Press "Commit" on Weblate to ensure all translations are pushed to the i18n branch
2. Merge Weblate pull request
3. Check for new translatable strings (``lupdate-qt5 pext/pext.pro``)
4. Compile translations (``lrelease-qt5 pext/pext.pro``)

## Cleanup
1. ```git clean -dfx``` to delete all untracked files and directories
2. Temporarily disable dulwich version generation in setup.py

## Preparation
1. Update the ``<VERSION>`` in ``pext/VERSION``
2. Update the ``<VERSION>`` in ``Info.plist``
3. Update the ``<VERSION>`` and ``<DATE>`` in ``CHANGELOG``
4. Update the minversion in the repology badge in `README.md`

## GitHub
1. ```git add pext/VERSION Info.plist CHANGELOG README.md```
2. ```git commit -m "Release Pext v<VERSION>"```
3. ```git tag -a v<VERSION> -m "Release Pext v<VERSION>"```
4. ```git push```
5. ```git push origin v<VERSION>```
6. Turn the tag into an actual release on GitHub, uploading the builds from Travis and AppVeyor for the tag itself

## PyPI
1. ```python3 setup.py sdist bdist_wheel```
2. ```twine upload dist/*```

## Open Build Service (OBS)
1. Update the version number in the _service file

## Matrix
1. Change the room topic: `Pext - Python-based Extendable Tool - https://pext.io/ - Latest release: <VERSION> (released <DATE>)`

## Server
1. Set version/stable to ```v<VERSION>```

## Afterwards
1. ```git reset --hard```
