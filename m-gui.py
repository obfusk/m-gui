#!/usr/bin/python3
# encoding: utf-8

# --                                                            ; {{{1
#
# File        : m-gui.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2018-09-10
#
# Copyright   : Copyright (C) 2018  Felix C. Stegerman
# Version     : v0.0.1
# License     : GPLv3+
#
# --                                                            ; }}}1

                                                                # {{{1
r"""
...
"""
                                                                # }}}1

# === TODO ===
#
# * cover most important commands
# * control w/ cursor+enter?
#   - terminal vs list view?
# * checkboxes etc. for --options
# * menu icons?

# === imports ===

import gi, os, sys
import xml.etree.ElementTree as ET

from pathlib import Path

os.environ["GDK_DPI_SCALE"] = "1.7"                             # TODO

gi.require_version("Gtk", "3.0")
gi.require_version("Vte", "2.91")

from gi.repository import GLib, Gio, Gtk, Pango, Vte

# === vars ===

__version__ = "0.0.1"

TITLE       = "m - minimalistic media manager - GUI"
APPID       = "ch.obfusk.m.gui"
SIZE        = (1280, 720)
MCMD        = "m"

# NB: we run a login shell b/c we need /etc/profile.d/vte-2.91.sh to
# be sourced for current_directory_uri to work.
SHELL       = "/bin/bash --login".split()

# === classes ===

# TODO
class Term(Vte.Terminal):                                       # {{{1
  """Terminal for m."""

  FLG = GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH

  def __init__(self, spawned_callback = None, exited_callback = None,
               chdir_callback = None, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.connect("child-exited", self.on_child_exited)
    self.connect("current-directory-uri-changed", self.on_cdu_changed)
    self.spawned_callback = spawned_callback
    self.exited_callback  = exited_callback
    self.chdir_callback   = chdir_callback

  def run(self, *cmd, **kwargs):
    """Run command in terminal."""
    info("*** RUN ***", cmd)
    if kwargs.get("reset", True): self.reset(False, True)
    _, pid = self.spawn_sync(Vte.PtyFlags.DEFAULT, None, cmd, [],
                             self.FLG, None, None)
    if self.spawned_callback: self.spawned_callback(pid)

  # TODO: only for testing
  def say(self, msg):
    self.run("echo", msg)

  def sh(self):
    self.run(*SHELL)

  def on_child_exited(self, _term, status):
    if self.exited_callback: self.exited_callback(status)

  def on_cdu_changed(self, _term):
    uri = self.props.current_directory_uri
    if uri:
      d = GLib.filename_from_uri(uri)[0]
      if self.chdir_callback: self.chdir_callback(d)
                                                                # }}}1

class AppWin(Gtk.ApplicationWindow):                            # {{{1
  """Main application window."""

  def __init__(self, term_args = {}, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.set_default_size(*SIZE)
    self.cwd_lbl, self.term = Gtk.Label(cwd()), Term(**term_args)
    self.cwd_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    box = Gtk.Box(orientation = Gtk.Orientation.VERTICAL)
    box.pack_start(self.cwd_lbl, False, True, 0)
    box.pack_start(self.term   , True , True, 0)
    self.add(box)
                                                                # }}}1

# TODO
class App(Gtk.Application):                                     # {{{1
  """Main application."""

  # TODO: flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE ?
  def __init__(self, *args, **kwargs):
    super().__init__(*args, application_id = APPID, **kwargs)
    self.win, self.actions = None, []

  def do_startup(self):                                         # {{{2
    Gtk.Application.do_startup(self)
    builder = Gtk.Builder.new_from_string(MENU_XML, -1)
    self.set_menubar(builder.get_object("menubar"))
    for name in ACTIONS:
      cb = "on_{}".format(name)
      if hasattr(self, cb):
        self.add_simple_action(name, getattr(self, cb))
      else:
        self.add_simple_action(name, self.on_something)
                                                                # }}}2

  def add_simple_action(self, name, callback):
    action = Gio.SimpleAction.new(name, None)
    action.connect("activate", callback)
    self.add_action(action)
    self.actions.append(action)

  # TODO
  def do_activate(self):                                        # {{{2
    if not self.win:
      term_args = dict(spawned_callback = self.on_cmd_spawned,
                       exited_callback  = self.on_cmd_exited,
                       chdir_callback   = self.on_chdir)
      self.win  = AppWin(application = self, title = TITLE,
                         term_args = term_args)
    self.win.show_all()
    self.win.present()
    self.win.fullscreen()                                       # TODO
                                                                # }}}2

  def on_opendir(self, _action, _param):
    d = self.choose_folder()
    if d is not None:
      os.chdir(d)
      self.on_chdir(d)

  def on_dirup(self, _action, _param):
    chdir_up()
    self.on_chdir(cwd())

  def on_shell(self, _action, _param):
    self.win.term.sh()

  def on_quit(self, _action, _param):
    self.quit()

  def on_list(self, _action, _param):
    self.run_m("ls")

  def on_listdirs(self, _action, _param):
    self.run_m("ld")

  def on_next(self, _action, _param):
    self.fullscreen = True
    self.run_m("next")

  # ... TODO ...

  # TODO: only for testing
  def on_something(self, action, _param):
    msg = ">>> {} <<<".format(action.get_name())
    self.win.term.say(msg)

  def on_cmd_spawned(self, pid):
    if self.fullscreen: self.win.unfullscreen()                 # TODO
    info("*** SPAWN ***", "pid =", pid)
    for action in self.actions:
      if action.get_name() != "quit":
        action.set_enabled(False)

  def on_cmd_exited(self, status):
    info("*** EXIT ***", "status =", status)
    for action in self.actions:
      action.set_enabled(True)
    if self.fullscreen:
      self.fullscreen = False
      self.win.fullscreen()                                     # TODO

  def on_chdir(self, d):
    info("*** CHDIR ***", d)
    self.win.cwd_lbl.set_text(d)

  def choose_folder(self):                                      # {{{2
    dialog = Gtk.FileChooserDialog(
      "Please choose a folder", self.win,
      Gtk.FileChooserAction.SELECT_FOLDER,
      (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
       Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    )
    dialog.set_filename(cwd())                                  # TODO
    try:
      response = dialog.run()
      if response == Gtk.ResponseType.OK:
        return dialog.get_filename()
      else:
        return None
    finally:
      dialog.destroy()
                                                                # }}}2

  # TODO: what about opts & args? ask or allow choosing?
  def run_m(self, *cmd):
    fcmd              = (MCMD,) + cmd
    os.environ["PWD"] = cwd()
    self.win.term.feed("$ {}\r\n".format(" ".join(fcmd)).encode())
    self.win.term.run(*fcmd)
                                                                # }}}1

# === functions ===

def main(*args): App().run()

def info(*msgs): print(*msgs, file = sys.stderr)

# ugly, but better than os.chdir(`cd ..; pwd`), right?!
def chdir_up(): os.chdir(str(Path(cwd()).parent))

def cwd(): return GLib.get_current_dir()  # ok w/ symlinks

# === data ===

                                                                # {{{1
MENU_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="menubar">
    <submenu>
      <attribute name="label" translatable="yes">_File</attribute>
      <section>
        <item>
          <attribute name="action">app.opendir</attribute>
          <attribute name="label" translatable="yes">_Open Directory...</attribute>
          <attribute name="accel">&lt;Primary&gt;o</attribute>
        </item>
        <item>
          <attribute name="action">app.dirup</attribute>
          <attribute name="label" translatable="yes">Go to _Parent Directory...</attribute>
          <attribute name="accel">&lt;Primary&gt;u</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.shell</attribute>
          <attribute name="label" translatable="yes">Open _Shell</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.quit</attribute>
          <attribute name="label" translatable="yes">_Quit</attribute>
          <attribute name="accel">&lt;Primary&gt;q</attribute>
        </item>
      </section>
    </submenu>
    <submenu>
      <attribute name="label" translatable="yes">_Command</attribute>
      <section>
        <item>
          <attribute name="action">app.list</attribute>
          <attribute name="label" translatable="yes">_List</attribute>
          <attribute name="accel">&lt;Primary&gt;l</attribute>
        </item>
        <item>
          <attribute name="action">app.listdirs</attribute>
          <attribute name="label" translatable="yes">List _Directories</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.next</attribute>
          <attribute name="label" translatable="yes">Play _Next</attribute>
          <attribute name="accel">&lt;Primary&gt;n</attribute>
        </item>
      </section>
    </submenu>
  </menu>
</interface>
"""[1:]
                                                                # }}}1

ACTIONS = set( x.text.strip().replace("app.", "")
               for x in ET.fromstring(MENU_XML)
                        .findall(".//attribute[@name='action']") )

# === entry point ===

def main_():
  """Entry point for main program."""
  return main(*sys.argv[1:])

if __name__ == "__main__":
  sys.exit(main_())

# vim: set tw=70 sw=2 sts=2 et fdm=marker :
