#!/usr/bin/python3
import gettext
import gi
import locale
import os
import setproctitle
import subprocess
import warnings
import sys
import traceback

# Suppress GTK deprecation warnings
warnings.filterwarnings("ignore")

gi.require_version("Gtk", "3.0")
gi.require_version('XApp', '1.0')
from gi.repository import Gtk, Gdk, Gio, XApp

import utils
from common import *

setproctitle.setproctitle("clicky")

# i18n
APP = 'clicky'
LOCALE_DIR = "/usr/share/locale"
locale.bindtextdomain(APP, LOCALE_DIR)
gettext.bindtextdomain(APP, LOCALE_DIR)
gettext.textdomain(APP)
_ = gettext.gettext


class MyApplication(Gtk.Application):

    def __init__(self, application_id, flags):
        Gtk.Application.__init__(self, application_id=application_id, flags=flags)
        self.connect("activate", self.activate)

    def activate(self, application):
        windows = self.get_windows()
        if (len(windows) > 0):
            window = windows[0]
            window.present()
            window.show()
        else:
            window = MainWindow(self)
            self.add_window(window.window)
            window.window.show()

class MainWindow():

    def __init__(self, application):

        self.application = application
        self.settings = Gio.Settings(schema_id="org.x.clicky")

        # Main UI
        gladefile = "/usr/share/clicky/clicky.ui"
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APP)
        self.builder.add_from_file(gladefile)
        self.window = self.builder.get_object("main_window")
        self.window.set_title(_("Screenshot"))
        self.window.set_icon_name("clicky")
        self.window.set_resizable(False)
        self.stack = self.builder.get_object("stack")
        self.radio_mode_screen = self.builder.get_object("radio_mode_screen")
        self.radio_mode_window = self.builder.get_object("radio_mode_window")
        self.radio_mode_area = self.builder.get_object("radio_mode_area")
        self.checkbox_pointer = self.builder.get_object("checkbox_pointer")
        self.checkbox_shadow = self.builder.get_object("checkbox_shadow")
        self.spin_delay = self.builder.get_object("spin_delay")

        # CSS
        provider = Gtk.CssProvider()
        provider.load_from_path("/usr/share/clicky/clicky.css")
        screen = Gdk.Display.get_default_screen(Gdk.Display.get_default())
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Settings
        prefer_dark_mode = self.settings.get_boolean("prefer-dark-mode")
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", prefer_dark_mode)

        mode = self.settings.get_string("capture-mode")
        self.builder.get_object(f"radio_mode_{mode}").set_active(True)

        self.settings.bind("include-pointer", self.checkbox_pointer, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("add-shadow", self.checkbox_shadow, "active", Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("delay", self.spin_delay, "value", Gio.SettingsBindFlags.DEFAULT)

        # import xapp.SettingsWidgets
        # spin = xapp.SettingsWidgets.SpinButton(_("Delay"), units="seconds")
        # self.builder.get_object("box_options").pack_start(spin, False, False, 0)

        self.window.show()

        self.builder.get_object("go_back_button").hide()

        # Widget signals
        self.window.connect("key-press-event",self.on_key_press_event)
        self.builder.get_object("go_back_button").connect("clicked", self.go_back)
        self.builder.get_object("button_take_screenshot").connect("clicked", self.start_screenshot)
        self.radio_mode_screen.connect("toggled", self.on_capture_mode_toggled)
        self.radio_mode_window.connect("toggled", self.on_capture_mode_toggled)
        self.radio_mode_area.connect("toggled", self.on_capture_mode_toggled)

    def get_capture_mode(self):
        if self.radio_mode_screen.get_active():
            mode = CAPTURE_MODE_SCREEN
        elif self.radio_mode_window.get_active():
            mode = CAPTURE_MODE_WINDOW
        else:
            mode = CAPTURE_MODE_AREA
        return mode

    def on_capture_mode_toggled(self, widget):
        self.settings.set_string("capture-mode", self.get_capture_mode())

    def start_screenshot(self, widget):
        self.hide_window()
        GObject.timeout_add(200, self.take_screenshot)

    def hide_window(self):
        self.window.hide()
        self.window.set_opacity(0)
        self.window.set_skip_pager_hint(True)
        self.window.set_skip_taskbar_hint(True)

    def show_window(self):
        self.window.show()
        self.window.set_opacity(1)
        self.window.set_skip_pager_hint(False)
        self.window.set_skip_taskbar_hint(False)

    def take_screenshot(self):
        try:
            options = Options(self.settings)
            pixbuf = utils.capture_pixbuf(options)
            self.builder.get_object("screenshot_image").set_from_pixbuf(pixbuf)
            self.builder.get_object("screenshot_image").show()
            self.navigate_to("screenshot_page")
            self.show_window()
        except:
            print(traceback.format_exc())
            print("Fatal exception occured, quitting!")
            sys.exit(1)

    @idle_function
    def navigate_to(self, page, name=""):
        if page == "main_page":
            self.builder.get_object("go_back_button").hide()
        else:
            self.builder.get_object("go_back_button").show()
        self.stack.set_visible_child_name(page)

    def go_back(self, widget):
        self.navigate_to("main_page")

    def open_about(self, widget):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self.window)
        dlg.set_title(_("About"))
        dlg.set_program_name(_("Screenshot"))
        dlg.set_comments(_("Save images of your screen or individual windows"))
        try:
            h = open('/usr/share/common-licenses/GPL', encoding="utf-8")
            s = h.readlines()
            gpl = ""
            for line in s:
                gpl += line
            h.close()
            dlg.set_license(gpl)
        except Exception as e:
            print (e)

        dlg.set_version("__DEB_VERSION__")
        dlg.set_icon_name("clicky")
        dlg.set_logo_icon_name("clicky")
        dlg.set_website("https://www.github.com/linuxmint/clicky")
        def close(w, res):
            if res == Gtk.ResponseType.CANCEL or res == Gtk.ResponseType.DELETE_EVENT:
                w.destroy()
        dlg.connect("response", close)
        dlg.show()

    def open_keyboard_shortcuts(self, widget):
        gladefile = "/usr/share/clicky/shortcuts.ui"
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(gladefile)
        window = builder.get_object("shortcuts")
        window.set_title(_("Screenshot"))
        window.show()

    def on_menu_quit(self, widget):
        self.application.quit()

    def on_key_press_event(self, widget, event):
        persistant_modifiers = Gtk.accelerator_get_default_mod_mask()
        modifier = event.get_state() & persistant_modifiers
        ctrl = modifier == Gdk.ModifierType.CONTROL_MASK
        shift = modifier == Gdk.ModifierType.SHIFT_MASK

        if ctrl and event.keyval == Gdk.KEY_r:
            # Ctrl + R
            pass
        elif ctrl and event.keyval == Gdk.KEY_f:
            # Ctrl + F
            pass
        elif event.keyval == Gdk.KEY_F11:
             # F11..
             pass

if __name__ == "__main__":
    application = MyApplication("org.x.clicky", Gio.ApplicationFlags.FLAGS_NONE)
    application.run()

