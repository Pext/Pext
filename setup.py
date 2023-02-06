import os
import sys
from setuptools import setup
from subprocess import check_output

pext_path = os.path.dirname(os.path.abspath(__file__))
pext_version_path = os.path.join(pext_path, 'pext', 'VERSION')

with open(pext_version_path) as version_file:
    version = version_file.read().strip()

print("Calculating current version")
version_found = None

# Get version name from AppVeyor
if 'APPVEYOR' in os.environ:
    if os.environ['APPVEYOR_REPO_TAG'] == "true":
        version_found = os.environ['APPVEYOR_REPO_TAG_NAME']
        print(f"AppVeyor: Set version to {version_found} from APPVEYOR_REPO_TAG_NAME")
    else:
        print(f"AppVeyor: Not a tagged version, APPVEYOR_REPO_TAG is {os.environ['APPVEYOR_REPO_TAG']} instead of true")
else:
    print("AppVeyor: No valid version info")

# Get version name from GitHub
if not version_found:
    if 'GITHUB_REF_TYPE' in os.environ:
        if os.environ['GITHUB_REF_TYPE'] == "tag":
            version_found = os.environ['GITHUB_REF_NAME']
            print(f"GitHub: Set version to {version_found} from GITHUB_REF_NAME")
        else:
            print(f"GitHub: Found {os.environ['GITHUB_REF_NAME']} in GITHUB_REF_NAME but GITHUB_REF_TYPE is {os.environ['GITHUB_REF_TYPE']} instead of tag")
    else:
        print("GitHub: No valid version info")

# Get version name from Dulwich
if not version_found:
    try:
        from dulwich.porcelain import describe
        version_found = describe(pext_path)
        print(f"Dulwich: Set version to {version_found} using describe")
    except Exception as e:
        print("Dulwich: Failed to determine version with dulwich: {}".format(e))

# Get version name from Git
if not version_found:
    try:
        version_found = check_output(['git', 'describe'], cwd=pext_path).splitlines()[0]
    except Exception as e:
        print("Git: Failed to determine version with git describe: {}".format(e))

if version_found:
    if isinstance(version_found, bytes):
        version = version_found.decode()
    else:
        version = version_found

version = version.lstrip("v")

# Translate 3-parted git versions to PEP 440-compliant version strings
if len(version_parts := version.split("-")) == 3:
    version = f"{version_parts[0]}.dev{version_parts[1]}+{version_parts[2]}"

with open(pext_version_path, "w") as version_file:
    version_file.write(version)

with open(os.path.join(pext_path, 'requirements.txt')) as requirements_file:
    requirements = []
    for line in requirements_file:
        requirement_spec = line.strip().split(';', 1)
        if len(requirement_spec) == 1 or eval(requirement_spec[1]):
            requirements.append(requirement_spec[0])

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
else:
    extra_options = dict()

setup(
    name='Pext',
    version=version,
    install_requires=requirements,
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
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities'
    ],
    keywords='extendable pluggable',
    packages=[
        'pext',
        'pext/helpers',
        'pext_dev',
    ],
    package_data={'pext': ['VERSION', 'i18n/*.qm', 'images/128x128/*', 'images/scalable/*', 'qml/*', 'helpers/*', '*.py', 'Pext.workflow/*'],
                  'pext_dev': ['module/*', 'theme/*', '*.py']},
    zip_safe=False,
    entry_points={
        'gui_scripts': [
            'pext=pext.__main__:run_qt5'
        ],
        'console_scripts': [
            'pext_dev=pext_dev.__main__:main'
        ]
    },
    **extra_options
)
