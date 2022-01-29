#!/usr/bin/python3
import gi
import threading
from gi.repository import GObject

# Used as a decorator to run things in the background
def async_function(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

# Used as a decorator to run things in the main loop, from another thread
def idle_function(func):
    def wrapper(*args):
        GObject.idle_add(func, *args)
    return wrapper

CAPTURE_MODE_SCREEN = 'screen'
CAPTURE_MODE_WINDOW = 'window'
CAPTURE_MODE_AREA = 'area'

class Options():

    def __init__(self, settings):
        self.mode = settings.get_string("capture-mode")
        self.delay = settings.get_int("delay")
        self.include_pointer = settings.get_boolean("include-pointer")
        self.add_shadow = settings.get_boolean("add-shadow")
        self.include_borders = settings.get_boolean("include-borders")
        self.enable_flash = settings.get_boolean("enable-flash")
        self.enable_sound = settings.get_boolean("enable-sound")
        self.enable_dbus_method = settings.get_boolean("enable-dbus-method")
