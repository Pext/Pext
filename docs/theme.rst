Theme
=====

All theme information is stored in a file named ``theme.conf``. This file should be in the root directory of the theme.

For up-to-date examples, look at any of the themes in the `Pext GitHub organisation <https://github.com/Pext>`__.

File format
-----------

The ``theme.conf`` file is in ini format and has 4 headers (color groups) which contain keys and values (color roles). Every color group and role is optional. If not defined, system colors are used.

Color Roles are written as simple key = value lines with the value containing 3 comma-separated numbers for the amount of red, green and blue (RGB) ranging from 0 to 255.

Please be aware that Qt, the graphical user interface library Pext uses, has some code to automatically slightly adjust colors based on their location for contrast, so you may not get the exact color you defined.

Color Groups
~~~~~~~~~~~~

======== ===========
Name     Description
======== ===========
Disabled Used when the element cannot be interacted with
Active   Used when the element is focused and interactable
Inactive Used when the element is unfocused (background)
All      Used when no more specific match exists
======== ===========

Color Rules
~~~~~~~~~~~

These descriptions are taken from https://doc.qt.io/qt-5/qpalette.html#ColorRole-enum. Not all of these may have an effect in Pext, so experiment!

=============== ===========
Name            Description
=============== ===========
Window          A general background color
WindowText      A general foreground color
Base            Used mostly as the background color for text entry widgets, but can also be used for other painting - such as the background of combobox drop down lists and toolbar handles. It is usually white or another light color
AlternateBase   Used as the alternate background color in views with alternating row colors
ToolTipBase     Used as the background color for QToolTip and QWhatsThis. Tool tips use the Inactive color group of QPalette, because tool tips are not active windows
ToolTipText     Used as the foreground color for QToolTip and QWhatsThis. Tool tips use the Inactive color group of QPalette, because tool tips are not active windows
PlaceholderText Used as the placeholder color for various text input widgets 
Text            The foreground color used with Base. This is usually the same as the WindowText, in which case it must provide good contrast with Window and Base
Button          The general button background color. This background can be different from Window as some styles require a different background color for buttons
ButtonText      A foreground color used with the Button color
BrightText      A text color that is very different from WindowText, and contrasts well with e.g. Dark. Typically used for text that needs to be drawn where Text or WindowText would give poor contrast, such as on pressed push buttons. Note that text colors can be used for things other than just words; text colors are usually used for text, but it's quite common to use the text color roles for lines, icons, etc
Light           Lighter than Button color
Midlight        Between Button and Light
Dark            Darker than Button
Mid             Between Button and Dark
Shadow          A very dark color. By default, the shadow color is black
Highlight       A color to indicate a selected item or the current item. By default, the highlight color is dark blue
HighlightedText A text color that contrasts with Highlight. By default, the highlighted text color is white
Link            A text color used for unvisited hyperlinks. By default, the link color is blue
LinkVisited     A text color used for already visited hyperlinks. By default, the linkvisited color is magenta
=============== ===========
