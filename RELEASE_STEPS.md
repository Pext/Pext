**This documentation is for maintainers. If you're an user, please ignore it.**

``<VERSION>`` is the release version (example: 0.1)  
``<DATE>`` is the release date as YYYY-MM-DD (example: 2015-12-22)

# When releasing, do the following:
## Cleanup
1. ```git clean -df``` to delete all untracked files and directory
2. Temporarily disable pygit2 version generation in setup.py

## Preparation
1. Update the ``<VERSION>`` in ``pext/VERSION``
2. Update the ``<VERSION>`` in ``pext.1``
3. Update the ``<VERSION>`` and ``<DATE>`` in ``CHANGELOG``

## GitHub
1. ```git add pext/VERSION pext.1 CHANGELOG```
2. ```git commit -m "Release Pext v<VERSION>"```
3. ```git tag -a v<VERSION> -m "Release Pext v<VERSION>"```
4. ```git push```
5. ```git push origin v<VERSION>```
6. Turn the tag into an actual release on GitHub

## PyPI
1. ```python3 setup.py sdist bdist_wheel```
2. ```twine upload dist/*```

## IRC
1. To OFTC ChanServ: ```set #pext topic Pext - Python-based Extendable Tool - https://pext.hackerchick.me/ - Latest release: <VERSION> (released <DATE>)```


## Afterwards
1. ```git reset --hard```
