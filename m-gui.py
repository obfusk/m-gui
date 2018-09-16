#!/usr/bin/python3
# encoding: utf-8

# --                                                            ; {{{1
#
# File        : m-gui.py
# Maintainer  : Felix C. Stegerman <flx@obfusk.net>
# Date        : 2018-09-16
#
# Copyright   : Copyright (C) 2018  Felix C. Stegerman
# Version     : v0.1.1
# License     : GPLv3+
#
# --                                                            ; }}}1

                                                                # {{{1
r"""
m - minimalistic media manager - GUI

See README.md for additional information and examples.
"""
                                                                # }}}1

# === imports ===

import argparse, contextlib, json, os, re, subprocess, sys, time
import xml.etree.ElementTree as ET

from pathlib import Path

# see also import_gtk()

# === vars ===

__version__ = "0.1.1"

DESC        = "m - minimalistic media manager - GUI"

HOME        = Path.home()
CFG         = ".obfusk-m"
GUICFGFILE  = "gui.json"

APPID       = "ch.obfusk.m.gui"
SIZE        = (1280, 720)

MCMD        = "m"
MOPTS       = "colour show-hidden ignorecase numeric-sort".split()

MSPEC       = "skip done playing new all".split()
CUSTOM      = "custom..."

SCALE       = 1.5
SCROLLBACK  = 1024
COMBOWRAP   = 80

# NB: we run a login shell b/c we need /etc/profile.d/vte-2.91.sh to
# be sourced for current_directory_uri to work.
SHELL       = "/bin/bash"                                       # TODO
SHELLCMD    = [SHELL, "-l"]
SHELLRUN    = [SHELL, "-c"]

# === config ===

def command(cfg, name, **override):
  mopts = { **cfg["m_options"], **override }
  opts  = " ".join( "--" + o for o in MOPTS if mopts.get(o) )
  mcmd  = cfg["m_command"] + (" " + opts if opts else "")
  return cfg["scripts"][name].replace("#{M}", mcmd)

def command_w_filespec(cfg, name, filespec, **override):
  cmd = command(cfg, name, **override)
  if "#{FILESPEC}" in cmd:
    spec = filespec(name)
    if spec is None: return None
    cmd = cmd.replace("#{FILESPEC}", spec)
  return cmd

def xml_with_mod(cfg, xml): return xml.replace("#{MOD}", cfg["mod"])

def config():                                                   # {{{1
  cfg, user = default_config(), user_config()
  w_def     = lambda k: user.get(k, cfg.get(k))
  return dict({ k:w_def(k) for k in cfg.keys()
                if k not in "scripts commands".split() }, **dict(
    scripts   = { **cfg["scripts"], **user.get("scripts", {}) },
    commands  = w_def("commands") + user.get("add_commands", []),
  ))
                                                                # }}}1

def default_config():                                           # {{{1
  return dict(
    scripts = {
      "list"            : "#{M} ls",
      "list-nums"       : "#{M} ls --numbers",
      "list-dirs"       : "#{M} ld",
      "list-dirs-cols"  : "#{M} ld | column",
      "next"            : "#{M} n",
      "next-new"        : "#{M} nn",
      "play"            : "#{M} p #{FILESPEC}",
      "mark"            : "#{M} m #{FILESPEC}",
      "unmark"          : "#{M} u #{FILESPEC}",
      "skip"            : "#{M} s #{FILESPEC}",
      "index"           : "#{M} index",
      "alias"           : "#{M} alias",
      "_list"           : "#{M} --no-colour --safe ls"
    },
    commands = [
      ["list            l           _List",
       "list-nums       <#{MOD}>l   List with Numbers",
       "list-dirs       d           List _Directories",
       "list-dirs-cols  <#{MOD}>d   List Directories in Columns"],
      ["next            n           Play _Next",
       "next-new        <#{MOD}>n   Play Next New"],
      ["play            p           _Play File...",
       "mark            m           _Mark File...",
       "unmark          u           _Unmark File...",
       "skip            s           _Skip File..."],
      ["index           i           _Index Current Directory",
       "alias           <#{MOD}>a   Alias Current Directory"]
    ],
    m_command = MCMD, m_options = dict(colour = True),
    colours   = "#ffffff:#000000:#2e3436:#cc0000:#4e9a06:#c4a000:"
                "#3465a4:#75507b:#06989a:#d3d7cf:#555753:#ef2929:"
                "#8ae234:#fce94f:#729fcf:#ad7fa8:#34e2e2:#eeeeec",
    scale = SCALE, fullscreen = False, stay_fullscreen = False,
    mod = "Shift", bookmarks = []
  )
                                                                # }}}1

def user_config():
  cf = user_config_file()
  if not cf.exists(): return {}
  with cf.open() as f: return json.load(f)

def save_bookmark(d):                                           # {{{1
  user = user_config(); bms = user.setdefault("bookmarks", [])
  if d in bms: return False
  user["bookmarks"].append(d)
  (HOME / CFG).mkdir(exist_ok = True)
  with user_config_file().open("w") as f:
    json.dump(user, f, indent = 2, sort_keys = True)
    f.write("\n")
  return True
                                                                # }}}1

def user_config_file(): return HOME / CFG / GUICFGFILE

# === classes ===

def define_classes():
  global Term, AppWin, App

  class Term(Vte.Terminal):                                     # {{{1
    """Terminal for m."""

    FLG = GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH

    def __init__(self, *, spawned_callback = None,
                 exited_callback = None, chdir_callback = None,
                 colours = None, **kwargs):
      super().__init__(**kwargs)
      self.set_scrollback_lines(SCROLLBACK)
      self.connect("child-exited", self.on_child_exited)
      self.connect("current-directory-uri-changed", self.on_cdu_changed)
      self.spawned_callback = spawned_callback
      self.exited_callback  = exited_callback
      self.chdir_callback   = chdir_callback
      if colours: self.set_colors(*colours)

    # TODO: use spawn_async when it becomes available
    def run(self, *cmd):
      """Run command in terminal."""
      _, pid = self.spawn_sync(Vte.PtyFlags.DEFAULT, None, cmd, [],
                               self.FLG, None, None)
      if self.spawned_callback: self.spawned_callback(pid)
      time.sleep(0.2)   # seems to help

    def clear(self):
      self.reset(False, True)

    def header(self, text):
      self.feed(text.replace("\n", "\r\n").encode())

    def run_header(self, cmd):
      self.header("$ " + cmd + "\n")

    def sh(self, cmd = None):
      c = cmd or " ".join(SHELLCMD)
      print("$", c); self.clear(); self.run_header(c)
      self.run(*(SHELLRUN + [cmd] if cmd else SHELLCMD))

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

    def __init__(self, *, term_args = {}, **kwargs):
      super().__init__(**kwargs)
      self.set_default_size(*SIZE)
      self.cwd_lbl  = Gtk.Label(label = cwd())
      self.term     = Term(**term_args)
      self.cwd_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
      box = Gtk.Box(orientation = Gtk.Orientation.VERTICAL)
      box.pack_start(self.cwd_lbl, False, True, 0)
      box.pack_start(self.term   , True , True, 0)
      self.add(box)
                                                                # }}}1

  class ComboBoxDialog(Gtk.Dialog):                             # {{{1
    """ComboBox chooser dialog."""

    def __init__(self, parent, title, store, *, monospace = False,
                 active = 0, text_index = 1):
      super().__init__(title = title, transient_for = parent)
      self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                       Gtk.STOCK_OK, Gtk.ResponseType.OK)
      self.store = store
      self.chooser = Gtk.ComboBox.new_with_model(store)
      if monospace:
        self.chooser.get_style_context().add_class("monospace")
      if active is not None:
        self.chooser.set_active(active % len(store))
      renderer                        = Gtk.CellRendererText()
      renderer.props.ellipsize        = Pango.EllipsizeMode.MIDDLE
      renderer.props.max_width_chars  = COMBOWRAP               # TODO
      self.chooser.pack_start(renderer, True)
      self.chooser.add_attribute(renderer, "text", text_index)
      self.get_content_area().pack_start(self.chooser, True, True, 0)
      self.set_default_response(Gtk.ResponseType.OK)
      self.show_all()

    def ask(self):
      """Runs the dialog and returns the selected store row or None."""
      with run_dialog(self) as ok:
        if ok:
          it = self.chooser.get_active_iter()
          if it is not None: return self.store[it]
        return None
                                                                # }}}1

  class EntryDialog(Gtk.MessageDialog):                         # {{{1
    """Entry dialog."""

    def __init__(self, parent, message, *, secondary = None,
                 entry_text = None, title = None):
      super().__init__(transient_for  = parent,
                       type           = Gtk.MessageType.QUESTION,
                       buttons        = Gtk.ButtonsType.OK_CANCEL,
                       message_format = message)
      if title: self.set_title(title)
      if secondary: self.format_secondary_text(secondary)
      self.entry = Gtk.Entry()
      if entry_text: self.entry.set_text(entry_text)
      self.entry.set_activates_default(True)
      self.get_message_area().pack_end(self.entry, True, True, 0)
      self.set_default_response(Gtk.ResponseType.OK)
      self.show_all()

    def ask(self):
      """Runs the dialog and returns the entered text or None."""
      with run_dialog(self) as ok:
        return ok and self.entry.get_text()
                                                                # }}}1

  class App(Gtk.Application):                                   # {{{1
    """Main application."""

    # TODO: Gio.ApplicationFlags.HANDLES_COMMAND_LINE ?
    def __init__(self, cfg, *, fullscreen = False,
                 stay_fullscreen = False, **kwargs):
      super().__init__(application_id = APPID,
                       flags = Gio.ApplicationFlags.NON_UNIQUE,
                       **kwargs)
      self.win, self.actions, self.noquit = None, [], False
      self.cfg, self.is_fs, self.stay_fs, self.start_fs \
        = cfg, False, stay_fullscreen, fullscreen
      self.cfg["bookmarks"] = set(self.cfg["bookmarks"])        # TODO

    def do_startup(self):                                       # {{{2
      Gtk.Application.do_startup(self)
      xml = menu_xml(self.cfg)
      Gtk.Application.do_startup(self)
      builder = Gtk.Builder.new_from_string(xml, -1)
      self.set_menubar(builder.get_object("menubar"))
      for name in xml_actions(xml):
        cb = "on_{}".format(name)
        if hasattr(self, cb):
          self.add_simple_action(name, getattr(self, cb))
        else:
          self.add_simple_action(name, self.on_run_script(name))
      provider = Gtk.CssProvider()
      Gtk.StyleContext().add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
      )
      css = b".monospace { font-family: monospace; }"
      provider.load_from_data(css)
                                                                # }}}2

    def add_simple_action(self, name, callback):
      action = Gio.SimpleAction.new(name, None)
      action.connect("activate", callback)
      self.add_action(action)
      self.actions.append(action)

    def add_window(self):                                       # {{{2
      colours   = [ parse_colour(c)     # [fg,bg]+palette
                    for c in self.cfg["colours"].split(":") ]
      term_args = dict(spawned_callback = self.on_cmd_spawned,
                       exited_callback  = self.on_cmd_exited,
                       chdir_callback   = self.chdir,
                       colours          = colours[:2]+[colours[2:]])
      self.win  = AppWin(application = self, title = DESC,
                         term_args = term_args)
      self.win.connect("window-state-event", self.on_window_state_event)
      self.win.show_all()
                                                                # }}}2

    def do_activate(self):
      if not self.win:
        self.add_window()
        if self.start_fs: self.win.fullscreen()
      elif self.stay_fs:  self.win.fullscreen()
      self.win.present()

    def on_opensubdir(self, _action, _param):
      self._choose(self.choose_subdir)

    def on_opendir(self, _action, _param):
      self._choose(self.choose_folder)

    def on_dirup(self, _action, _param):
      self.chdir_as_cmd(dir_up())

    def on_openbm(self, _action, _param):
      self._choose(self.choose_bookmark)

    def on_savebm(self, _action, _param):
      d     = cwd()
      saved = save_bookmark(d)
      msg   = "bookmark added" if saved else "already bookmarked"
      self.cfg["bookmarks"].add(d)
      self.win.term.clear()
      self.win.term.header("# " + msg + "\n")

    def _choose(self, f):
      d = f()
      if d is not None: self.chdir_as_cmd(d)

    def on_shell(self, _action, _param):
      self.noquit = True
      self.win.term.sh()

    def on_quit(self, _action, _param):
      self.quit()

    def on_run_script(self, name):
      return lambda _action, _param: self.run_cmd(name)

    def on_pgup(self, _action, _param):
      self._scroll(lambda v, val: val - v.get_page_increment())

    def on_pgdn(self, _action, _param):
      self._scroll(lambda v, val: val + v.get_page_increment())

    def on_lnup(self, _action, _param):
      self._scroll(lambda v, val: val - v.get_step_increment())

    def on_lndn(self, _action, _param):
      self._scroll(lambda v, val: val + v.get_step_increment())

    def on_top(self, _action, _param):
      self._scroll(lambda v, _: v.get_lower())

    def on_bottom(self, _action, _param):
      self._scroll(lambda v, _: v.get_upper())

    def _scroll(self, f):
      v = self.win.term.props.vadjustment
      v.set_value(f(v, v.get_value()))

    def on_fullscreen(self, _action, _param):
      if self.is_fs:
        self.win.unfullscreen()
      else:
        self.win.fullscreen()

    def on_cmd_spawned(self, pid):
      # info("*** SPAWN ***", "pid =", pid)
      for action in self.actions:
        if self.noquit or action.get_name() != "quit":
          action.set_enabled(False)
      self.noquit = False

    def on_cmd_exited(self, status):
      # info("*** EXIT ***", "status =", status)
      for action in self.actions:
        action.set_enabled(True)
      if self.stay_fs: self.win.fullscreen()

    def on_window_state_event(self, _widget, event):
      self.is_fs = bool(event.new_window_state &
                        Gdk.WindowState.FULLSCREEN)

    def chdir(self, d):
      chdir(d)
      print("$ cd", d)
      self.win.cwd_lbl.set_text(cwd())

    def chdir_as_cmd(self, d):
      self.chdir(d)
      self.win.term.clear()
      self.win.term.run_header("cd " + d)

    def choose_subdir(self):
      d = self._combo_ask("Please choose a subdirectory", self.subdirs())
      return d and str(cwd() / Path(d))

    def choose_folder(self):                                    # {{{2
      dialog = Gtk.FileChooserDialog(
        title = "Please choose a folder", transient_for = self.win,
        action = Gtk.FileChooserAction.SELECT_FOLDER
      )
      dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_OK, Gtk.ResponseType.OK)
      dialog.set_filename(cwd())
      with run_dialog(dialog) as ok:
        return ok and dialog.get_filename()
                                                                # }}}2

    def choose_bookmark(self):
      return self._combo_ask("Please choose a bookmark",
                             sorted(self.cfg["bookmarks"]))

    def _combo_ask(self, title, data):
      if len(data) == 0: return None                            # TODO
      store = Gtk.ListStore(int, str)
      for i, x in enumerate(data): store.append([i, x])
      ans = ComboBoxDialog(self.win, title, store, monospace = True).ask()
      return None if ans is None else data[ans[0]]

    def choose_filespec(self, name):                            # {{{2
      files, store = self.list(), Gtk.ListStore(int, str)
      n, m = len(files), len(MSPEC); w = len(str(n-1))
      for i, x in enumerate(files):
        store.append([i, "{:{w}d} {}".format(i+1, x, w = w)])
      for i, x in enumerate(MSPEC):
        store.append([n+i, x])
      store.append([n+m, CUSTOM])
      ans = ComboBoxDialog(self.win, "Please choose a file to " + name,
                           store, monospace = True, active = -1).ask()
      if ans is not None:
        i = ans[0]
        if i == n+m:
          return EntryDialog(
            self.win, "Please specify which file(s)",
            secondary = "e.g. '1,4-7'"
          ).ask() or None
        return str(i+1) if i < n else MSPEC[i-n]
      return None
                                                                # }}}2

    def run_cmd(self, name):
      cmd = command_w_filespec(self.cfg, name, self.choose_filespec)
      if cmd is not None: self.win.term.sh(cmd)

    def subdirs(self):
      d = Path(cwd())
      return sorted(
        ( x.name for x in self._iterdir(d) if x.is_dir() ),
        key = lambda x: x.lower()                               # TODO
      )

    def _iterdir(self, d):
      return ( x for x in d.iterdir()
               if self.cfg["m_options"].get("show-hidden")
               or not x.name.startswith(".") )

    def list(self):
      cmd = command(self.cfg, "_list", colour = False)
      out = subprocess.run(SHELLRUN + [cmd], check = True,
                           universal_newlines = True,
                           stdout = subprocess.PIPE).stdout
      return out.rstrip("\n").split("\n")
                                                                # }}}1

# === functions ===

def import_gtk(scale):                                          # {{{1
  global GLib, Gio, Gdk, Gtk, Pango, Vte
  os.environ["GDK_DPI_SCALE"] = str(scale)
  import gi
  gi.require_version("Gtk", "3.0")
  gi.require_version("Gdk", "3.0")
  gi.require_version("Vte", "2.91")
  from gi.repository import GLib, Gio, Gdk, Gtk, Pango, Vte
                                                                # }}}1

def main(*args):                                                # {{{1
  cfg = config(); n = _argument_parser(cfg).parse_args(args)
  if n.show_config:
    json.dump(cfg, sys.stdout, indent = 2, sort_keys = True)
    print()
    return 0
  import_gtk(n.scale); define_classes()
  print("==> starting...")
  App(cfg, fullscreen = n.fullscreen or n.stay_fullscreen,
      stay_fullscreen = n.stay_fullscreen).run()
  print("==> bye.")
  return 0
                                                                # }}}1

def _argument_parser(cfg):                                      # {{{1
  p = argparse.ArgumentParser(description = DESC)
  p.set_defaults(**{ k:cfg[k] for k in
                     "scale fullscreen stay_fullscreen".split() })
  p.add_argument("--version", action = "version",
                 version = "%(prog)s {}".format(__version__))
  p.add_argument("--show-config", action = "store_true",
                 help = "show configuration and exit")
  p.add_argument("--scale", "-s", metavar = "SCALE", type = float,
                 help = "set $GDK_DPI_SCALE to SCALE")
  p.add_argument("--fullscreen", "--fs", action = "store_true",
                 help = "start full screen")
  p.add_argument("--no-fullscreen", "--no-fs",
                 action = "store_false", dest = "fullscreen")
  p.add_argument("--stay-fullscreen", "--stay-fs",
                 action = "store_true",
                 help   = "start and stay full screen")
  p.add_argument("--no-stay-fullscreen", "--no-stay-fs",
                 action = "store_false", dest = "stay_fullscreen")
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

def menu_xml(cfg):                                              # {{{1
  return xml_with_mod(
    cfg, MENU_XML_HEAD + "".join(
      MENU_XML_SECTION_HEAD + "".join(
        MENU_XML_ITEM.format(*xml_quote(spec).split(maxsplit = 2))
        for spec in sec
      ) + MENU_XML_SECTION_FOOT
      for sec in cfg["commands"]
    ) + MENU_XML_FOOT
  )
                                                                # }}}1

def xml_quote(s):
  return s.replace("<", "&lt;").replace(">", "&gt;")

def xml_actions(xml):
  return set( x.text.strip().replace("app.", "")
              for x in ET.fromstring(xml)
              .findall(".//attribute[@name='action']") )

def parse_colour(s):
  c = Gdk.RGBA()
  if not c.parse(s): raise ValueError("colour parse failed: {}".format(s))
  return c

@contextlib.contextmanager
def run_dialog(dialog):
  try:
    if dialog.run() == Gtk.ResponseType.OK:
      yield True
    else:
      yield None
  finally:
    dialog.destroy()

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
          <attribute name="action">app.opensubdir</attribute>
          <attribute name="label" translatable="yes">_Open Subdirectory...</attribute>
          <attribute name="accel">o</attribute>
        </item>
        <item>
          <attribute name="action">app.opendir</attribute>
          <attribute name="label" translatable="yes">Open _Directory...</attribute>
          <attribute name="accel">&lt;#{MOD}&gt;o</attribute>
        </item>
        <item>
          <attribute name="action">app.dirup</attribute>
          <attribute name="label" translatable="yes">Open _Parent Directory (..)</attribute>
          <attribute name="accel">period</attribute>
        </item>
      </section>
      <section>
        <item>
          <attribute name="action">app.openbm</attribute>
          <attribute name="label" translatable="yes">Open _Bookmark...</attribute>
          <attribute name="accel">b</attribute>
        </item>
        <item>
          <attribute name="action">app.savebm</attribute>
          <attribute name="label" translatable="yes">Bookmark Current Directory</attribute>
          <attribute name="accel">&lt;#{MOD}&gt;b</attribute>
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

# === run ===

def _main(): sys.exit(main(*sys.argv[1:]))

if __name__ == "__main__": _main()

# vim: set tw=70 sw=2 sts=2 et fdm=marker :
