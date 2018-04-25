#Disable debug packages
%define debug_package %{nil}

Name:	pext
Version:	0.9
Release:	1%{?dist}
Summary:	Python-based extendable tool

License:	GPLv3
URL:		https://github.com/Pext/Pext
Source0: 	https://github.com/Pext/Pext/archive/v%{version}.zip
#This removes the dependency since dependency checks are done by dnf/yum/rpm.
#Also in Fedora the module name is PyQt5
Patch0:		remove-dependency.patch

BuildRequires:	python3-devel
Requires:	python3-qt5 python3-pyopengl

%description
Pext stands for Python-based extendable tool. It is built using Python 3 and Qt5 QML and has its behaviour decided by modules. Pext provides a simple window with a search bar, allowing modules to define what data is shown and how it is manipulated.

%prep
%setup -q -n Pext-%{version}
%patch0

%build
python3 setup.py build

%install
python3 setup.py install --prefix=%{_prefix} --root=%{buildroot}

%files
/usr/bin/pext
/usr/bin/pext_dev
%{python3_sitelib}/*
/usr/man/man1/pext.1.gz
/usr/share/applications/pext.desktop
/usr/share/icons/hicolor/128x128/apps/pext.png
/usr/share/icons/hicolor/48x48/apps/pext.png
/usr/share/icons/hicolor/scalable/apps/pext.svg

%changelog
* Tue Oct 24 2017 Kevin W. Anderson <andersonkw2@gmail.com>
- Initial Packaging
