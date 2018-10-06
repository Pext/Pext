import os
import sys
from setuptools import setup
from subprocess import check_output

pext_path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(pext_path, 'pext', 'VERSION')) as version_file:
    version = version_file.read().strip()

try:
    from dulwich.porcelain import describe
    print("Updating version with dulwich")
    version = describe(pext_path)
except Exception as e:
    print("Failed to determine version with dulwich, falling back to git describe: {}".format(e))
    try:
        version = check_output(['git', 'describe'], cwd=pext_path).splitlines()[0]
    except Exception as e:
        print("Failed to determine version with git describe: {}".format(e))

version = version.lstrip('v').replace('-', '+', 1).replace('-', '.')
with open(os.path.join(pext_path, 'pext', 'VERSION'), "w") as version_file:
    version_file.write(version)

print("Pext version: {}".format(version))

if sys.platform == 'linux':
    extra_options = dict(
        data_files=[
            ('share/icons/hicolor/scalable/apps', ['pext/images/scalable/pext.svg']),
            ('share/icons/hicolor/48x48/apps', ['pext/images/48x48/pext.png']),
            ('share/icons/hicolor/128x128/apps', ['pext/images/128x128/pext.png']),
            ('share/applications', ['io.pext.pext.desktop']),
            ('share/metainfo', ['io.pext.pext.appdata.xml'])
        ]
    )
    extra_deps = []
elif sys.platform == 'darwin':
    extra_options = dict()
    extra_deps = ['accessibility']
else:
    extra_options = dict()
    extra_deps = []

setup(
    name='Pext',
    version=version,
    install_requires=[
        'dulwich',
        'pynput',
        'pyqt5',
        'requests'
    ] + extra_deps,
    description='Python-based extendable tool',
    long_description='A Python-based application that uses modules for extendability',
    url='https://pext.io/',
    author='Sylvia van Os',
    author_email='sylvia@hackerchick.me',
    license='GPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities'
    ],
    keywords='extendable pluggable',
    packages=[
        'pext',
        'pext/helpers',
        'pext_dev'
    ],
    package_data={'pext': ['VERSION', 'i18n/*.qm', 'images/128x128/*', 'images/scalable/*', 'qml/*', 'helpers/*', '*.py', 'Pext.workflow/*'],
                  'pext_dev': ['module/*', 'theme/*', '*.py']},
    zip_safe=False,
    entry_points={
        'gui_scripts': [
            'pext=pext.__main__:main'
        ],
        'console_scripts': [
            'pext_dev=pext_dev.__main__:main'
        ]
    },
    **extra_options
)
