<!-- {{{1 -->

    File        : README.md
    Maintainer  : Felix C. Stegerman <flx@obfusk.net>
    Date        : 2018-09-16

    Copyright   : Copyright (C) 2018  Felix C. Stegerman
    Version     : v0.0.1
    License     : GPLv3+

<!-- }}}1 -->

<!--

[![PyPI Version](https://img.shields.io/pypi/v/TODO.svg)](https://pypi.python.org/pypi/TODO)

-->

[![Build Status](https://travis-ci.org/obfusk/m-gui.svg?branch=master)](https://travis-ci.org/obfusk/m-gui)
[![GPLv3+](https://img.shields.io/badge/license-GPLv3+-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)

## Description

m - minimalistic media manager - GUI

A minimalistic GUI for [m](https://github.com/obfusk/m).

## Examples

```bash
$ m-gui --stay-fullscreen --scale 2.0
```

## Help

```bash
$ m-gui --help          # show options
$ m-gui --show-config   # show configuration
```

## Requirements

Python >= 3.5, PyGObject, GTK+ 3,
[VTE](https://wiki.gnome.org/Apps/Terminal/VTE); and `m` of course.

NB: there will be a Debian package soon™, but for now you can install
the additional dependencies (if you're missing any) on Debian using:

```bash
$ sudo apt install python3-gi libgtk-3-0 libvte-2.91-0
```

## Installing

You can just put `m-gui.py` somewhere on your `$PATH` (in e.g.
`~/bin`; I suggest calling it `m-gui`, but you're free to choose
another name).

You may want to clone the repository instead of just downloading
`m-gui.py` to be able to get new versions easily.

### Using git

```bash
$ cd /some/convenient/dir
$ git clone https://github.com/obfusk/m-gui.git obfusk-m-gui
$ cd ~/bin                  # or some other dir on your $PATH
$ ln -s /some/convenient/dir/obfusk-m-gui/m-gui.py m-gui
```

Updating:

```bash
$ cd /some/convenient/dir/obfusk-m-gui
$ git pull
```

## Configuration File

You can configure some settings in `~/.obfusk-m/gui.json`.  To see the
current configuration, run:

```bash
$ m-gui --show-config
```

### Bookmarks

NB: since bookmarks are saved in `gui.json`, adding a bookmark from
the GUI will open and re-save this file.  Formatting is thus not
preserved, data should be (unless you happen to trigger a race
condition by writing to this file in between loading and saving by the
GUI).

```json
{
  "bookmarks": [
    "/some/media/dir",
    "/some/other/media/dir"
  ]
}
```

### Defaults

```json
{
  "scale": 2.0,
  "stay_fullscreen": true
}
```

### Adding commands

```json
{
  "add_commands": [
    [
      "mark-and-next space _Mark Playing and Play Next"
    ]
  ],
  "scripts": {
    "mark-and-next": "#{M} mark playing && #{M} next"
  }
}
```

### m options

```json
{
  "m_options": {
    "colour": true,
    "ignorecase": true,
    "numeric-sort": true,
    "show-hidden": true
  }
}
```

### m command

```json
{
  "m_command": "mmm"
}
```

NB: the command is passed to the shell, so you'll need to escape/quote
special characters (including spaces) appropriately; be careful!

## TODO

* `ack TODO`
* also allow setting --numeric-sort etc. on the fly
  - checkboxes in gui?
  - --options passed through to m?
* handle exceptions better.
* README etc., document, test?, package (deb + pip); screenshot?
* use shell "m ..." only if no need to quote?!
* running w/ `python3 -Wd` results in DeprecationWarnings
  - Vte.Terminal.spawn_async not yet available

## License

[![GPLv3+](https://www.gnu.org/graphics/gplv3-127x51.png)](https://www.gnu.org/licenses/gpl-3.0.html)

## Links

* [GTK+ key names](https://github.com/GNOME/gtk/blob/master/gdk/keynames.txt)
  for key bindings like `<Primary>q`.

<!-- vim: set tw=70 sw=2 sts=2 et fdm=marker : -->
