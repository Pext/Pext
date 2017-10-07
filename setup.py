import os
import sys
from setuptools import setup

with open(os.path.join('pext', 'VERSION')) as version_file:
    version = version_file.read().strip()

if sys.platform == 'darwin':
    extra_options = dict(
        setup_requires=['py2app'],
        app=['pext/__main__.py'],
        options={'py2app': {
            'iconfile': 'pext/images/scalable/pext.icns'
        }}
    )
else:
    extra_options = dict(
        data_files=[
            ('share/icons/hicolor/scalable/apps', ['pext/images/scalable/pext.svg']),
            ('share/icons/hicolor/48x48/apps', ['pext/images/48x48/pext.png']),
            ('share/icons/hicolor/128x128/apps', ['pext/images/128x128/pext.png']),
            ('share/applications', ['pext.desktop']),
            ('man/man1', ['pext.1'])
        ]
    )

setup(
    name='Pext',
    version=version,
    install_requires=[
        'pyqt5'
    ],
    description='Python-based extendable tool',
    long_description='A Python-based application that uses modules for extendability',
    url='https://pext.hackerchick.me/',
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
    package_data={'pext': ['i18n/*.qm', 'images/scalable/*', 'qml/*'],
                  'pext_dev': ['LICENSE', 'module/*', 'theme/*']},
    include_package_data=True,
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
