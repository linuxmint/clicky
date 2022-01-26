import cairo
import gi
from gi.repository import Gtk, Gdk, GLib

# How long to hold the flash for, in milliseconds.
FLASH_DURATION = 150;

# The factor which defines how much the flash fades per frame
FLASH_FADE_FACTOR = 0.95;

# How many frames per second
FLASH_ANIMATION_RATE = 120;

# When to consider the flash finished so we can stop fading
FLASH_LOW_THRESHOLD = 0.1;

class CheeseFlash(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, Gtk.WindowType.POPUP)

        self.flash_timeout_tag = 0
        self.fade_timeout_tag  = 0
        self.opacity = 1.0

        # make it so it doesn't look like a window on the desktop(+fullscreen)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)

        # Don't take focus
        self.set_accept_focus(False)
        self.set_focus_on_map(False)

        # Make it white
        self.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1.0, 1.0, 1.0, 1.0))

        # Don't consume input
        self.realize()
        input_region = cairo.Region()
        self.get_window().input_shape_combine_region(input_region, 0, 0)

    # Fade out the flash
    # returns True if the flash was completed, False if it must continue
    def opacity_fade(self):
        # exponentially decrease
        self.opacity *= FLASH_FADE_FACTOR;

        if(self.opacity <= FLASH_LOW_THRESHOLD):
            # the flasher has finished when we reach the quit value
            self.fade_timeout_tag = 0
            self.destroy()
            return False
        else:
            self.set_opacity(self.opacity)

        return True

    def start_fade(self):
        # If the screen is non-composited, just destroy and finish up
        if not self.get_screen().is_composited():
            self.destroy()
            return False

        self.fade_timeout_tag = GLib.timeout_add(1000.0 / FLASH_ANIMATION_RATE, self.opacity_fade)
        self.flash_timeout_tag = 0
        return False

    def fire(self, rect):
        if self.flash_timeout_tag > 0:
            GLib.source_remove(self.flash_timeout_tag)
            self.flash_timeout_tag = 0

        if self.fade_timeout_tag > 0:
            GLib.source_remove(self.fade_timeout_tag)
            self.fade_timeout_tag = 0

        self.opacity = 1.0
        self.resize(rect.width, rect.height)
        self.move(rect.x, rect.y)
        self.set_opacity(1)
        self.show_all()
        self.flash_timeout_tag = GLib.timeout_add(FLASH_DURATION, self.start_fade)
