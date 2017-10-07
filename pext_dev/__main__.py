#!/usr/bin/env python3

# Copyright (c) 2017 Sylvia van Os <sylvia@hackerchick.me>
#
# This file is part of Pext
#
# Pext is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Pext Development Tools.

This file aids in module development.
"""

import json
import os
import platform
import sys

from subprocess import check_call, CalledProcessError
from shutil import copy, copytree, rmtree
try:
    from typing import List
except ImportError:
    from backports.typing import List  # type: ignore


class AppFile():
    """Get access to application-specific files."""

    @staticmethod
    def get_path(name: str) -> str:
        """Return the absolute path by file or directory name."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)


class Module():
    """Module code."""

    def init(self, directory: str) -> None:
        """Initialize a new module at the given directory."""
        print('Initializing new module in {}'.format(directory))
        print('Please enter some info about your new module')
        name = input('Module name: ')
        developer = input('Developer name: ')
        description = input('Description: ')
        homepage = input('Homepage: ')

        metadata = {'name': name,
                    'developer': developer,
                    'description': description,
                    'homepage': homepage,
                    'license': 'GPL-3.0+'}

        with open(os.path.join(directory, 'metadata.json'), 'w') as metadata_file:
            metadata_file.write(json.dumps(metadata, sort_keys=True, indent=2))

        copy(
            AppFile().get_path(os.path.join('module', '__init__.py')),
            os.path.join(directory, '__init__.py'))

        copy(
            AppFile().get_path('LICENSE'),
            os.path.join(directory, 'LICENSE'))

    def run(self, tempdir: str, argv: List[str]) -> None:
        """Run the module in the current directory in a new Pext instance."""
        # Prepare vars
        module_path = os.path.join(tempdir, 'pext', 'modules', 'pext_module_development')
        module_requirements_path = os.path.join(module_path, 'requirements.txt')
        module_dependencies_path = os.path.join(tempdir, 'pext', 'module_dependencies')

        # Copy module to there
        print('Copying resources...')
        copytree(
            os.getcwd(),
            module_path)

        # BEGIN: Pip install
        # FIXME: Don't copy-paste from the main Pext codebase
        if os.path.isfile(module_requirements_path):
            print('Installing dependencies...')

            pip_command = [sys.executable,
                           '-m',
                           'pip',
                           'install']

            # FIXME: Cheap hack to work around Debian's faultily-patched pip
            if os.path.isfile('/etc/debian_version'):
                pip_command += ['--system']

            pip_command += ['--upgrade',
                            '--target',
                            module_dependencies_path,
                            '-r',
                            module_requirements_path]

            returncode = 0

            # FIXME: Cheap macOS workaround, part 1
            # See https://github.com/pypa/pip/pull/4111#issuecomment-280616124
            if platform.system() == "Darwin":
                with open(os.path.expanduser('~/.pydistutils.cfg'), 'w') as macos_workaround:
                    macos_workaround.write('[install]\nprefix=')

            # Actually run the pip command
            try:
                check_call(pip_command)
            except CalledProcessError as e:
                returncode = e.returncode

            # FIXME: Cheap macOS workaround, part 2
            if platform.system() == "Darwin":
                os.remove(os.path.expanduser('~/.pydistutils.cfg'))

            if returncode != 0:
                print('Could not install dependencies')
                return
        # END: Pip install

        # Run Pext
        print('Launching Pext...')
        check_call([
            sys.executable,
            os.path.join(AppFile().get_path('..'), 'pext')] +
            ['--module',
             'pext_module_development',
             '--profile',
             'none'] + argv)

        # Clean up
        rmtree(tempdir)


class Theme():
    """Theme code."""

    def init(self, directory: str) -> None:
        """Initialize a new theme at the given directory."""
        print('Initializing new theme in {}'.format(directory))
        print('Please enter some info about your new theme')
        name = input('Theme name: ')
        developer = input('Developer/Designer name: ')
        description = input('Description: ')
        homepage = input('Homepage: ')

        metadata = {'name': name,
                    'developer': developer,
                    'description': description,
                    'homepage': homepage,
                    'license': 'GPL-3.0+'}

        with open(os.path.join(directory, 'metadata.json'), 'w') as metadata_file:
            metadata_file.write(json.dumps(metadata, sort_keys=True, indent=2))

        copy(
            AppFile().get_path(os.path.join('theme', 'theme.conf')),
            os.path.join(directory, 'theme.conf'))

        copy(
            AppFile().get_path('LICENSE'),
            os.path.join(directory, 'LICENSE'))

    def run(self, tempdir: str, argv: List[str]) -> None:
        """Run the theme in the current directory in a new Pext instance."""
        # Prepare vars
        theme_path = os.path.join(tempdir, 'pext', 'themes', 'pext_theme_development')

        # Copy module to there
        print('Copying resources...')
        copytree(
            os.getcwd(),
            theme_path)

        # Run Pext
        print('Launching Pext...')
        check_call([
            sys.executable,
            os.path.join(AppFile().get_path('..'), 'pext')] +
            ['--theme',
             'pext_theme_development',
             '--profile',
             'none'] + argv)

        # Clean up
        rmtree(tempdir)


def run(argv: List[str]) -> None:
    """Figure out the class and command to run from the CLI input and run it."""
    if (argv[0] == "module"):
        classInstance = Module()
    elif (argv[0] == "theme"):
        classInstance = Theme()  # type: ignore
    else:
        usage()
        sys.exit(1)

    if (argv[1] == "init"):
        if len(argv) >= 3:
            directory = os.path.expanduser(argv[2])
            os.makedirs(directory)
        else:
            directory = os.getcwd()

        classInstance.init(directory)
    elif (argv[1] == "run"):
        tempdir = '.pext_temp'

        # Make sure there are no leftover files
        try:
            rmtree(tempdir)
        except FileNotFoundError:
            pass

        # Prepare temp directory for module
        os.environ["XDG_CONFIG_HOME"] = tempdir

        classInstance.run(tempdir, argv[2:])
    else:
        usage()
        sys.exit(2)


def usage() -> None:
    """Print usage information."""
    print('''Options:

module init[=PATH]
    Initialize a new module in the current directory or given path.

module run
    Run the module in the current directory a new Pext instance. Added options are passed to Pext as-is.

theme init[=PATH]
    Initialize a new theme in the current directory or given path.

theme run
    Run the theme in the current directory a new Pext instance. Added options are passed to Pext as-is.''')


if __name__ == "__main__":
    # Run chosen functionality
    run(sys.argv[1:])
