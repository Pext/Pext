**This documentation is for maintainers. If you're an user, please ignore it.**

``<VERSION>`` is the release version (example: 0.1.0)  
``<DATE>`` is the release date as YYYY-MM-DD (example: 2015-12-22)  
``<IMAGES>`` are the screenshots of the features present in Pext. Must be in order for proper priority when converting into GIF on new releases (example: pext-*.PNG)

# When releasing, do the following:
## i18n
1. Press "Commit" on Weblate to ensure all translations are up to date
2. Merge Weblate pull request
3. Check for new translatable strings (``lupdate-qt5 pext/pext.pro``)

## Cleanup
1. ```git clean -dfx``` to delete all untracked files and directories
2. Temporarily disable dulwich version generation in setup.py

## Preparation
1. Update the ``<VERSION>`` in ``pext/VERSION``
2. Update the ``<VERSION>`` in ``Info.plist``
3. Update the ``<VERSION>`` and ``<DATE>`` in ``CHANGELOG.md``
4. Update the minversion in the repology badge in `README.md`
5. In case new features have been added, update the current GIF under the head Introduction in `README.md` using ```convert -delay 100 <IMAGES> -loop 0 pext_intro.gif```

## GitHub
1. ```git add pext/VERSION Info.plist CHANGELOG.md README.md```
2. ```git commit -m "Release Pext v<VERSION>"```
3. ```git tag -a v<VERSION> -m "Release Pext v<VERSION>"```
4. ```git push```
5. ```git push origin v<VERSION>```
6. Turn the tag into an actual release on GitHub, uploading the builds from Travis and AppVeyor for the tag itself

## PyPI
1. ```python3 setup.py sdist bdist_wheel```
2. ```twine upload dist/*```

## Matrix
1. Change the room topic: `Pext - Python-based Extendable Tool - https://pext.io/ - Latest release: <VERSION> (released <DATE>)`

## Server
1. Update links in index.html
2. Set version/stable to ```v<VERSION>```

## Afterwards
1. ```git reset --hard```
