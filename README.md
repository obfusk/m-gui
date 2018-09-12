<!-- {{{1 -->

    File        : README.md
    Maintainer  : Felix C. Stegerman <flx@obfusk.net>
    Date        : 2018-09-12

    Copyright   : Copyright (C) 2018  Felix C. Stegerman
    Version     : v0.0.1
    License     : GPLv3+

<!-- }}}1 -->

<!--

[![PyPI Version](https://img.shields.io/pypi/v/TODO.svg)](https://pypi.python.org/pypi/TODO)
[![Build Status](https://travis-ci.org/obfusk/m-gui.svg?branch=master)](https://travis-ci.org/obfusk/m-gui)

-->

[![GPLv3+](https://img.shields.io/badge/license-GPLv3+-blue.svg)](https://www.gnu.org/licenses/gpl-3.0.html)

## Description

m - minimalistic media manager - GUI

A minimalistic GUI for [m](https://github.com/obfusk/m).

## Examples

```bash
$ m-gui --stay-fullscreen --scale 2.0
```

## Requirements

Python >= 3.5, PyGObject, GTK+ 3, VTE.

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

You can set/override some defaults in `~/.obfusk-m/gui.json`; for
example:

```json
{
  "add_commands": [
    [
      "markandnext space _Mark Playing and Play Next"
    ]
  ],
  "scripts": {
    "markandnext": "m mark playing && m next"
  }
}
```

and if your `m` command is e.g. `mmm`:

```json
{
  "m_command": "mmm"
}
```

NB: do not use a command name that includes spaces or anything else
that needs to be escaped when passed to the shell.

## TODO

* cover most important commands!
  - la, nn, p, m, u, s, i, alias, ...
* allow choices (input / choose) for arguments for mark etc.
* checkboxes etc. for --options, --options -> m, config.json?!
  - --show-hidden --ignorecase --numeric-sort
  - --numbers
  - | column
* use shell "m ..." only if no need to quote?!
* allow no accel?!
* handle exceptions better.
* README etc., document, test?, package (deb + pip)
* screenshot?
* (MAYBE) about dialog, help etc.
* (MAYBE) menu icons?
* (MAYBE) control w/ cursor+enter? // terminal vs list view?

## License

[![GPLv3+](https://www.gnu.org/graphics/gplv3-127x51.png)](https://www.gnu.org/licenses/gpl-3.0.html)

<!-- vim: set tw=70 sw=2 sts=2 et fdm=marker : -->
