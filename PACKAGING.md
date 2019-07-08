# Tips for packagers

Thank you for considering packaging Pext! Please add information about your package to the README after you're done.

## Release notifications
It is recommended to request joining Pext's [Packagers](https://github.com/orgs/Pext/teams/packagers) team on GitHub to receive release notifications. This is also the intended place for packagers to help each other.

## Dependency changes
All dependency changes are documented in the CHANGELOG. They will also be noted in the release notifications.

## Dependencies
Pext is exclusively a Python 3 application. There is no and will not be any Python 2 support.

The [requirements.txt](https://github.com/Pext/Pext/blob/master/requirements.txt) file contains a list of all dependencies. You should ignore dependencies which contain a `sys.platform` line for other platforms than the one you are packaging for. You can also ignore the explicit version numbers as these are only used to ensure that dependency version changes are always noticed during development, to simplify debugging. Pext should work with any reasonably recent version of its dependencies. If it doesn't work with whatever version is available for packaging on the intended platform, please file a bug report.
