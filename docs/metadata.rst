Metadata
========

All module or theme metadata is stored in a file named ``metadata.json``. This file should be in the root directory of the module or theme.

For up-to-date examples, look at any of the modules or themes in the `Pext GitHub organisation <https://github.com/Pext>`__.

Fields
------

=============== ============ ===========
Name            Type         Description
=============== ============ ===========
bugtracker      String       URL location of the bugtracker
bugtracker_type String       Enables Pext to prefill a bugtracker's values if a known type. Supported values: "github"
description     String       Description of the module
developer       String       Name of the developer
git_urls        List<String> A list of git URLs the module/theme can be cloned from
homepage        String       URL location of the module/theme's homepage
id              String       Unique identifier of the module
license         String       Module license as `SPDX identifier <https://spdx.org/licenses/>`__
name            String       Module name
platforms       List<String> Supported platforms. Can be "Linux", "Darwin" (for macOS) or "Windows"
settings        List<Object> A list of all possible settings. See `Settings`_
=============== ============ ===========

Settings
--------

Each value in the settings list has the following possible fields:

=============== ============ ===========
Name            Type         Description
=============== ============ ===========
default         Object       The default value
description     String       User-facing description of the option
name            String       Internally used name of the option
options         List<Object> A list of possible options. Optional
=============== ============ ===========
