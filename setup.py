import os
from setuptools import setup

with open(os.path.join('pext', 'VERSION')) as version_file:
    version = version_file.read().strip()

setup(
    name='Pext',
    version=version,
    install_requires=[
        'pyqt5'
    ],
    description='Python-based extendable tool',
    long_description='A Python-based application that uses modules for extendability',
    url='https://github.com/Pext/Pext',
    author='Sylvia van Os',
    author_email='sylvia@hackerchick.me',
    license='GPLv3+',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities'
    ],
    keywords='extendable pluggable',
    packages=[
        'pext',
        'pext/helpers'
    ],
    package_data={'pext': ['images/scalable/*', 'qml/*']},
    include_package_data=True,
    zip_safe=False,
    data_files=[
        ('share/icons/hicolor/scalable/apps', ['pext/images/scalable/pext.svg']),
        ('share/icons/hicolor/48x48/apps', ['pext/images/48x48/pext.png']),
        ('share/icons/hicolor/128x128/apps', ['pext/images/128x128/pext.png']),
        ('share/applications', ['pext.desktop'])
    ],
    entry_points={
        'gui_scripts': [
            'pext=pext.__main__:main'
        ]
    }
)
