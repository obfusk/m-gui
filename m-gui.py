#!/usr/bin/python3
# encoding: utf-8

# --                                                            ; {{{1
#
# File        : m-gui.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2018-09-11
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
# * cover most important commands!
#   - la, nn, p, m, u, s, i, alias, ...
# * allow choices (input / choose) for arguments for mark etc.
# * checkboxes etc. for --options, --options -> m, config.json?!
#   - --show-hidden --ignorecase --numeric-sort
#   - --numbers
#   - | column
# * merge gui.json
# * use shell "m ..." only if no need to quote?!
# * README etc., document, test?, package
# * (MAYBE) about dialog, help etc.
# * (MAYBE) menu icons?
# * (MAYBE) control w/ cursor+enter? // terminal vs list view?

# Depends: python3:any (>= 3.5~), python3-gi, libgtk-3-0, libvte-2.91-0

# === imports ===

import argparse, gi, os, sys, time
import xml.etree.ElementTree as ET

from pathlib import Path

# see also import_gtk()

# === vars ===

__version__ = "0.0.1"

TITLE       = "m - minimalistic media manager - GUI"
APPID       = "ch.obfusk.m.gui"
SIZE        = (1280, 720)

MCMD        = "m"
SCALE       = 1.5
SCROLLBACK  = 1024

# NB: we run a login shell b/c we need /etc/profile.d/vte-2.91.sh to
# be sourced for current_directory_uri to work.
SHELL       = "/bin/bash"
SHELLCMD    = [SHELL, "-l"]
SHELLRUN    = [SHELL, "-c"]

# === config ===

# TODO: more!; merge w/ ~/.obfusk-m/gui.json if exists; add_commands
def config(m = MCMD):
  return dict(
    scripts   = dict(list = m+" ls", listdirs = m+" ld", next = m+" n"),
    commands  = [["list l _List", "listdirs d List _Directories"],
                 ["next n Play _Next"]]
  )

# === classes ===

def define_classes():
  global Term, AppWin, App

  class Term(Vte.Terminal):                                     # {{{1
    """Terminal for m."""

    FLG = GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH

    def __init__(self, spawned_callback = None, exited_callback = None,
                 chdir_callback = None, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.set_scrollback_lines(SCROLLBACK)
      self.connect("child-exited", self.on_child_exited)
      self.connect("current-directory-uri-changed", self.on_cdu_changed)
      self.spawned_callback = spawned_callback
      self.exited_callback  = exited_callback
      self.chdir_callback   = chdir_callback

    def run(self, *cmd, **kwargs):                              # {{{2
      """Run command in terminal."""
      info("*** RUN ***", cmd)
      if kwargs.get("clear", True): self.clear()
      header = kwargs.get("header")
      if header: self.feed(header.replace("\n", "\n\r").encode())
      _, pid = self.spawn_sync(Vte.PtyFlags.DEFAULT, None, cmd, [],
                               self.FLG, None, None)
      if self.spawned_callback: self.spawned_callback(pid)
      time.sleep(0.1)   # seems to help
                                                                # }}}2

    def clear(self):
      self.reset(False, True)

    def sh(self, cmd = None, **kwargs):
      self.run(*(SHELLRUN + [cmd] if cmd else SHELLCMD), **kwargs)

    def on_child_exited(self, _term, status):
      if self.exited_callback: self.exited_callback(status)

    # NB: this only works if /etc/profile.d/vte-2.91.sh is sourced
    def on_cdu_changed(self, _term):
      uri = self.props.current_directory_uri
      if uri:
        d = GLib.filename_from_uri(uri)[0]
        if self.chdir_callback: self.chdir_callback(d)
                                                                # }}}1

  class AppWin(Gtk.ApplicationWindow):                          # {{{1
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
  class App(Gtk.Application):                                   # {{{1
    """Main application."""

    # TODO: flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE ?
    def __init__(self, *args, fullscreen = False,
                 stay_fullscreen = False, **kwargs):
      super().__init__(*args, application_id = APPID, **kwargs)
      self.win, self.actions, self.noquit = None, [], False
      self.is_fs, self.stay_fs, self.start_fs \
        = False, stay_fullscreen, fullscreen

    def do_startup(self):                                       # {{{2
      xml, self.scripts = menu_xml_and_scripts()
      Gtk.Application.do_startup(self)
      builder = Gtk.Builder.new_from_string(xml, -1)
      self.set_menubar(builder.get_object("menubar"))
      for name in xml_actions(xml):
        cb = "on_{}".format(name)
        if hasattr(self, cb):
          self.add_simple_action(name, getattr(self, cb))
        else:
          self.add_simple_action(name, self.on_run_script(name))
                                                                # }}}2

    def add_simple_action(self, name, callback):
      action = Gio.SimpleAction.new(name, None)
      action.connect("activate", callback)
      self.add_action(action)
      self.actions.append(action)

    def do_activate(self):                                      # {{{2
      if not self.win:
        term_args = dict(spawned_callback = self.on_cmd_spawned,
                         exited_callback  = self.on_cmd_exited,
                         chdir_callback   = self.chdir)
        self.win  = AppWin(application = self, title = TITLE,
                           term_args = term_args)
        self.win.connect("window-state-event", self.on_window_state_event)
      self.win.show_all()
      self.win.present()
      if self.start_fs: self.win.fullscreen()
                                                                # }}}2

    def on_opendir(self, _action, _param):
      d = self.choose_folder()
      if d is not None: self.chdir_and_clear(d)

    def on_dirup(self, _action, _param):
      self.chdir_and_clear(dir_up())

    def on_shell(self, _action, _param):
      self.noquit = True
      self.win.term.sh()

    def on_quit(self, _action, _param):
      self.quit()

    def on_run_script(self, name):
      def f(_action, _param):
        self.run_m(self.scripts[name])
      return f

    def on_pgup(self, _action, _param):
      v = self._vadj; v.set_value(v.get_value() - v.get_page_increment())

    def on_pgdn(self, _action, _param):
      v = self._vadj; v.set_value(v.get_value() + v.get_page_increment())

    def on_lnup(self, _action, _param):
      v = self._vadj; v.set_value(v.get_value() - v.get_step_increment())

    def on_lndn(self, _action, _param):
      v = self._vadj; v.set_value(v.get_value() + v.get_step_increment())

    def on_top(self, _action, _param):
      v = self._vadj; v.set_value(v.get_lower())

    def on_bottom(self, _action, _param):
      v = self._vadj; v.set_value(v.get_upper())

    @property
    def _vadj(self):
      return self.win.term.props.vadjustment

    def on_fullscreen(self, _action, _param):
      if self.is_fs:
        self.win.unfullscreen()
      else:
        self.win.fullscreen()

    def on_cmd_spawned(self, pid):
      info("*** SPAWN ***", "pid =", pid)
      for action in self.actions:
        if self.noquit or action.get_name() != "quit":
          action.set_enabled(False)
      self.noquit = False

    def on_cmd_exited(self, status):
      info("*** EXIT ***", "status =", status)
      for action in self.actions:
        action.set_enabled(True)
      if self.stay_fs: self.win.fullscreen()

    def on_window_state_event(self, widget, event):
      self.is_fs = bool(event.new_window_state &
                        Gdk.WindowState.FULLSCREEN)

    def chdir(self, d):
      chdir(d)
      info("*** CHDIR ***", d)
      self.win.cwd_lbl.set_text(cwd())

    def chdir_and_clear(self, d):
      self.chdir(d)
      self.win.term.clear()

    def choose_folder(self):                                    # {{{2
      dialog = Gtk.FileChooserDialog(
        "Please choose a folder", self.win,
        Gtk.FileChooserAction.SELECT_FOLDER,
        (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
         Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
      )
      dialog.set_filename(cwd())                                # TODO
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
    def run_m(self, cmd):
      self.win.term.sh(cmd, header = "$ {}\n".format(cmd))
                                                                # }}}1

# === functions ===

def import_gtk(scale = SCALE):
  global GLib, Gio, Gdk, Gtk, Pango, Vte
  os.environ["GDK_DPI_SCALE"] = str(scale)
  gi.require_version("Gtk", "3.0")
  gi.require_version("Gdk", "3.0")
  gi.require_version("Vte", "2.91")
  from gi.repository import GLib, Gio, Gdk, Gtk, Pango, Vte

def main(*args):
  n = _argument_parser().parse_args(args)
  import_gtk(scale = n.scale)
  define_classes()
  App(fullscreen = n.fullscreen or n.stay_fullscreen,
      stay_fullscreen = n.stay_fullscreen).run()

def _argument_parser():                                         # {{{1
  p = argparse.ArgumentParser(description = TITLE)
  p.set_defaults(scale = SCALE, fullscreen = False,
                 stay_fullscreen = False)
  p.add_argument("--version", action = "version",
                 version = "%(prog)s {}".format(__version__))
  p.add_argument("--scale", "-s", metavar = "SCALE", type = float,
                 help = "set $GDK_DPI_SCALE to SCALE")
  p.add_argument("--fullscreen", "--fs", action = "store_true",
                 help = "start full screen")
  p.add_argument("--stay-fullscreen", "--stay-fs",
                 action = "store_true",
                 help   = "start and stay full screen")
  return p
                                                                # }}}1

def info(*msgs): print(*msgs, file = sys.stderr)

# ugly, but better than os.chdir(`cd ..; pwd`), right?!
def dir_up(): return str(Path(cwd()).parent)

# NB: only ever use this to chdir so as to not break cwd()
def chdir(d):
  pd = Path(d)
  if not pd.is_absolute() or set([".", ".."]) & set(pd.parts):
    raise RuntimeError("OOPS -- this should never happen ")
  os.chdir(d)
  os.environ["PWD"] = d

# NB: not ideal, but hopefully it works
def cwd():
  pwd = os.environ["PWD"]
  if Path(pwd).resolve() != Path().resolve():
    raise RuntimeError("OOPS -- this should never happen ")
  return pwd

def menu_xml_and_scripts():
  c = config()
  return MENU_XML_HEAD + "".join(
    MENU_XML_SECTION_HEAD + "".join(
      MENU_XML_ITEM.format(*spec.split(maxsplit = 2)) for spec in sec
    ) + MENU_XML_SECTION_FOOT
    for sec in c["commands"]
  ) + MENU_XML_FOOT, c["scripts"]

def xml_actions(xml):
  return set( x.text.strip().replace("app.", "")
              for x in ET.fromstring(xml)
              .findall(".//attribute[@name='action']") )

# === data ===

                                                                # {{{1
MENU_XML_HEAD = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="menubar">
    <submenu>
      <attribute name="label" translatable="yes">_File</attribute>
      <section>
        <item>
          <attribute name="action">app.opendir</attribute>
          <attribute name="label" translatable="yes">_Open Directory...</attribute>
          <attribute name="accel">o</attribute>
        </item>
        <item>
          <attribute name="action">app.dirup</attribute>
          <attribute name="label" translatable="yes">Open _Parent Directory (..)</attribute>
          <attribute name="accel">period</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.shell</attribute>
          <attribute name="label" translatable="yes">Run _Shell</attribute>
          <attribute name="accel">dollar</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.quit</attribute>
          <attribute name="label" translatable="yes">_Quit</attribute>
          <attribute name="accel">q</attribute>
        </item>
      </section>
    </submenu>
    <submenu>
      <attribute name="label" translatable="yes">_Command</attribute>
"""[1:]                                                         # }}}1

                                                                # {{{1
MENU_XML_FOOT = """
    </submenu>
    <submenu>
      <attribute name="label" translatable="yes">_Window</attribute>
      <section>
        <item>
          <attribute name="action">app.pgup</attribute>
          <attribute name="label" translatable="yes">Scroll _Up a Page</attribute>
          <attribute name="accel">Page_Up</attribute>
        </item>
        <item>
          <attribute name="action">app.pgdn</attribute>
          <attribute name="label" translatable="yes">Scroll _Down a Page</attribute>
          <attribute name="accel">Page_Down</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.lnup</attribute>
          <attribute name="label" translatable="yes">Scroll Up a Line</attribute>
          <attribute name="accel">Up</attribute>
        </item>
        <item>
          <attribute name="action">app.lndn</attribute>
          <attribute name="label" translatable="yes">Scroll Down a Line</attribute>
          <attribute name="accel">Down</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.top</attribute>
          <attribute name="label" translatable="yes">Scroll to _Top</attribute>
          <attribute name="accel">Home</attribute>
        </item>
        <item>
          <attribute name="action">app.bottom</attribute>
          <attribute name="label" translatable="yes">Scroll to _Bottom</attribute>
          <attribute name="accel">End</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.fullscreen</attribute>
          <attribute name="label" translatable="yes">Toggle _Fullscreen</attribute>
          <attribute name="accel">f</attribute>
        </item>
      </section>
    </submenu>
  </menu>
</interface>
"""[1:]
                                                                # }}}1

MENU_XML_SECTION_HEAD = """
      <section>
"""[1:]

MENU_XML_ITEM = """
        <item>
          <attribute name="action">app.{}</attribute>
          <attribute name="accel">{}</attribute>
          <attribute name="label" translatable="yes">{}</attribute>
        </item>
"""[1:]

MENU_XML_SECTION_FOOT = """
      </section>
"""[1:]

# === entry point ===

def main_():
  """Entry point for main program."""
  return main(*sys.argv[1:])

if __name__ == "__main__":
  sys.exit(main_())

# vim: set tw=70 sw=2 sts=2 et fdm=marker :
