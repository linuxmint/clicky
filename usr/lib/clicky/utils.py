#!/usr/bin/python3
import cairo
import dbus
import os
import sys
import gi
import traceback
import Xlib.display
gi.require_version('GSound', '1.0')
from gi.repository import Gtk, Gio, Gdk, GdkX11, GdkPixbuf, GLib, GSound
from common import *

SCREENSHOT_WIDTH = -1
SCREENSHOT_HEIGHT = 250

########### SHELL #########################

def capture_via_gnome_dbus(options):
    pixbuf = None
    try:
        path = os.path.join(GLib.get_user_cache_dir(), "clicky")
        GLib.mkdir_with_parents(path, 0o0700)
        tmpname = "scr-%d.png" % GLib.random_int()
        filename = os.path.join(path, tmpname)

        bus = dbus.SessionBus()
        interface = bus.get_object('org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot')
        manager = dbus.Interface(interface, 'org.gnome.Shell.Screenshot')

        if options.enable_sound:
            play_sound_effect()

        if options.mode == CAPTURE_MODE_SCREEN:
            (success, filename_used) = manager.Screenshot(options.include_pointer, options.enable_flash, filename)
        elif options.mode == CAPTURE_MODE_WINDOW:
            (success, filename_used) = manager.ScreenshotWindow(options.include_borders, options.include_pointer, options.enable_flash, filename)
        else:
            x = 0
            y = 0
            height = 800
            width = 600
            (success, filename_used) = manager.ScreenshotArea(x, y, width, height, options.enable_flash, filename)

        if success:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, SCREENSHOT_WIDTH, SCREENSHOT_HEIGHT)
            os.unlink(filename)
    except Exception as e:
        print(traceback.format_exc())

    return pixbuf

############# X11 ############################


def get_xwindow(xid):
    # Scan all opened xwindows, return the one with the matching XID
    xdisplay = Xlib.display.Display()
    root_xwin = xdisplay.screen().root
    xwindow_list = [root_xwin]
    while len(xwindow_list) != 0:
        xwin = xwindow_list.pop(0)
        if xwin.id == xid:
           return xwin
        children = xwin.query_tree().children
        if children != None:
            xwindow_list += children
    print ("Unable to find xwindow matching - %d\n" % xid)
    return None

def find_xwindow(window):
    if window == Gdk.get_default_root_window():
        return None
    xwindow = get_xwindow(window.get_xid())
    if xwindow != None:
        # Switch to xwindow's parent until its parent matches its root
        while True:
            root = xwindow.query_tree().root
            parent = xwindow.query_tree().parent
            if root == parent:
                break
            xwindow = parent
    return xwindow

def make_region_with_monitors(display):
    num_monitors = display.get_n_monitors()
    region = cairo.Region()
    for i in range(num_monitors):
        monitor = display.get_monitor(i)
        cairo_rect = gdk_rect_to_cairo_rect(monitor.get_geometry())
        region.union(cairo_rect)
    return region

def blank_rectangle_in_pixbuf(pixbuf, rect):
    x2 = rect.x + rect.width
    y2 = rect.y + rect.height
    rowstride = pixbuf.get_rowstride()
    has_alpha = pixbuf.get_has_alpha()
    n_channels = pixbuf.get_n_channels()
    pixels = bytearray(pixbuf.get_pixels())

    for y in range(rect.y, y2):
        for x in range(rect.x, x2):
            # insert pixel data at right location in bytes array
            i = y * rowstride + x * n_channels
            pixels[i*3 + 0] = 0 # red
            pixels[i*3 + 1] = 0 # green
            pixels[i*3 + 2] = 0 # blue
            if has_alpha:
                pixels[i*3 + 4] = 255 # opaque black

def cairo_rect_to_gdk_rect(cairo_rect):
    rect = Gdk.Rectangle()
    rect.x = cairo_rect.x
    rect.y = cairo_rect.y
    rect.width = cairo_rect.width
    rect.height = cairo_rect.height

def gdk_rect_to_cairo_rect(gdk_rect):
    return cairo.RectangleInt(gdk_rect.x, gdk_rect.y, gdk_rect.width, gdk_rect.height)

def blank_region_in_pixbuf(pixbuf, region):
    n_rects = region.num_rectangles()
    pixbuf_rect = Gdk.Rectangle()
    pixbuf_rect.x = 0
    pixbuf_rect.y = 0
    pixbuf_rect.width = pixbuf.get_width()
    pixbuf_rect.height = pixbuf.get_height()
    for i in range(n_rects):
        cairo_rect = region.get_rectangle(i)
        gdk_rect = cairo_rect_to_gdk_rect(cairo_rect)
        (does_interect, intersection_rect) = pixbuf_rect.intersect(gdk_rect)
        if does_interect:
            blank_rectangle_in_pixbuf(pixbuf, intersection_rect)

# When there are multiple monitors with different resolutions, the visible area
# within the root window may not be rectangular(it may have an L-shape, for
# example).  In that case, mask out the areas of the root window which would
# not be visible in the monitors, so that screenshot do not end up with content
# that the user won't ever see.
def mask_monitors(pixbuf, root_window):
    display = root_window.get_display()
    region_with_monitors = make_region_with_monitors(display)
    screen = Gdk.Screen.get_default()
    invisible_region = cairo.Region(cairo.RectangleInt(0, 0, screen.get_width(), screen.get_height()))
    invisible_region.subtract(region_with_monitors)
    blank_region_in_pixbuf(pixbuf, invisible_region)

# Crop regions of the window which are outside of the screen
def crop_geometry(window_geometry):
    screenshot_geometry = Gdk.Rectangle()
    screenshot_geometry.x = window_geometry.x
    screenshot_geometry.y = window_geometry.y
    screenshot_geometry.width = window_geometry.width
    screenshot_geometry.height = window_geometry.height

    screen = Gdk.Screen.get_default()

    if screenshot_geometry.x < 0:
        screenshot_geometry.x = 0
        screenshot_geometry.width += screenshot_geometry.x

    if screenshot_geometry.y < 0:
        screenshot_geometry.y = 0
        screenshot_geometry.height += screenshot_geometry.y

    if screenshot_geometry.x + screenshot_geometry.width > screen.get_width():
        screenshot_geometry.width = screen.get_width() - screenshot_geometry.x

    if screenshot_geometry.y + screenshot_geometry.height > screen.get_height():
        screenshot_geometry.height = screen.get_height() - screenshot_geometry.y

    return screenshot_geometry

def screenshot_fallback_fire_flash(window, rectangle):
    if rectangle == None:
        rectangle = crop_geometry(window.get_frame_extents())
    flash = cheese_flash_new()
    flash.fire(rect)

def find_current_window():
    current_window = Gdk.Screen.get_default().get_active_window()
    seat = Gdk.Display.get_default().get_default_seat()
    device = seat.get_pointer()

    # If there's no active window, we fall back to returning the
    # window that the cursor is in.
    if current_window == None:
        current_window = device.get_window_at_position(None, None)

    if current_window != None:
        if current_window == Gdk.get_default_root_window() or current_window.get_type_hint() == Gdk.WindowTypeHint.DESKTOP:
            # if the current window is the desktop(e.g. nautilus), we
            # return None, as getting the whole screen makes more sense.
            return None

        # Once we have a window, we take the toplevel ancestor.
        current_window = current_window.get_toplevel()

    return current_window

def capture_via_x11(options):
    display = Gdk.Display.get_default()
    seat = display.get_default_seat()
    device = seat.get_pointer()
    root_window = Gdk.get_default_root_window()
    screen = Gdk.Screen.get_default()

    rect = Gdk.Rectangle()
    rect.x = 0
    rect.y = 0
    rect.height = 800
    rect.width = 600
    frame_offset = { 0, 0, 0, 0 }

    # find current window
    window = None
    if options.mode == CAPTURE_MODE_WINDOW:
        window = find_current_window()
    if window == None:
        window = root_window

    real_coords = window.get_frame_extents()
    screenshot_coords = crop_geometry(real_coords)

    wm = find_xwindow(window)
    if wm != None:
        wm_window = GdkX11.X11Window.foreign_new_for_display(GdkX11.X11Display.get_default(), wm.id)
        wm_real_coords = crop_geometry(wm_window.get_frame_extents())
        frame_offset_left = real_coords.x - wm_real_coords.x
        frame_offset_top = real_coords.y - wm_real_coords.y
        frame_offset_right = wm_real_coords.width - real_coords.width - frame_offset_left
        frame_offset_bottom = wm_real_coords.height - real_coords.height - frame_offset_top

    # if options.mode == CAPTURE_MODE_AREA:
    #     options.include_pointer = False
    #     screenshot_coords.x = rectangle.x - screenshot_coords.x
    #     screenshot_coords.y = rectangle.y - screenshot_coords.y
    #     screenshot_coords.width  = rectangle.width
    #     screenshot_coords.height = rectangle.height

    screenshot = Gdk.pixbuf_get_from_window(root_window,
                                           screenshot_coords.x, screenshot_coords.y,
                                           screenshot_coords.width, screenshot_coords.height)

    if options.mode != CAPTURE_MODE_SCREEN:
        mask_monitors(screenshot, root_window)

    if wm != None:
        # we must use XShape to avoid showing what's under the rounder corners
        # of the WM decoration.
        rectangles = wm.shape_get_rectangles(Xlib.ext.shape.SK.Bounding).rectangles
        if rectangles != None and len(rectangles) > 0:
            scale_factor = wm_window.get_scale_factor()
            has_alpha = screenshot.get_has_alpha()
            tmp = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, screenshot.get_width(), screenshot.get_height())
            tmp.fill(0)

            for rectangle in rectangles:
                # If we're using invisible borders, the ShapeBounding might not
                # have the same size as the frame extents, as it would include the
                # areas for the invisible borders themselves.
                # In that case, trim every rectangle we get by the offset between the
                # WM window size and the frame extents.
                # Note that the XShape values are in actual pixels, whereas the GDK
                # ones are in display pixels(i.e. scaled), so we need to apply the
                # scale factor to the former to use display pixels for all our math.
                rec_x = rectangle.x / scale_factor
                rec_y = rectangle.y / scale_factor
                rec_width = rectangle.width / scale_factor - (frame_offset_left + frame_offset_right)
                rec_height = rectangle.height / scale_factor - (frame_offset_top + frame_offset_bottom)

                if real_coords.x < 0:
                    rec_x += real_coords.x
                    rec_x = max(rec_x, 0)
                    rec_width += real_coords.x

                if real_coords.y < 0:
                    rec_y += real_coords.y
                    rec_y = max(rec_y, 0)
                    rec_height += real_coords.y

                if screenshot_coords.x + rec_x + rec_width > screen.get_width():
                    rec_width = screen.get_width() - screenshot_coords.x - rec_x

                if screenshot_coords.y + rec_y + rec_height > screen.get_height():
                    rec_height = screen.get_height() - screenshot_coords.y - rec_y

                # Undo the scale factor in order to copy the pixbuf data pixel-wise
                if has_alpha:
                    channels = 4
                else:
                    channels = 3
                # for y in range(rec_y * scale_factor, (rec_y + rec_height) * scale_factor):
                #     src_pixels = screenshot.get_pixels() \
                #              + y * screenshot.get_rowstride() \
                #              + rec_x * scale_factor * channels
                #     dest_pixels = tmp.get_pixels() \
                #               + y * tmp.get_rowstride() \
                #               + rec_x * scale_factor * 4

    #                 # for x in range(rec_width * scale_factor):
    #                 #     *dest_pixels++ = *src_pixels++
    #                 #     *dest_pixels++ = *src_pixels++
    #                 #     *dest_pixels++ = *src_pixels++

    #                 #     if(has_alpha)
    #                 #         *dest_pixels++ = *src_pixels++
    #                 #     else
    #                 #         *dest_pixels++ = 255

    #         # g_set_object(&screenshot, tmp)

    # if we have a selected area, there were by definition no cursor in the screenshot
    # if options.include_pointer:
    #     cursor = Gdk.Cursor.new_for_display(display, Gdk.LEFT_PTR)
    #     cursor_pixbuf = cursor.get_image()

    #     if cursor_pixbuf != None:
    #         # if(wm_window != None):
    #         #     (x, y) = wm_window.get_device_position(device)
    #         # else:
    #         #     (x, y) = wm_window.get_device_position(device)
    #         # sscanf(cursor_pixbuf.get_option("x_hot"), "%d", &xhot)
    #         # sscanf(cursor_pixbuf.get_option("y_hot"), "%d", &yhot)

    #         # in rect we have the cursor window coordinates
    #         rect.x = cx + real_coords.x
    #         rect.y = cy + real_coords.y
    #         rect.width = cursor_pixbuf.get_width()
    #         rect.height = cursor_pixbuf.get_height()

    #         # see if the pointer is inside the window
    #         # if(gdk_rectangle_intersect(&real_coords, &rect, &rect)):
    #         #     cursor_x = cx - xhot - frame_offset_left
    #         #     cursor_y = cy - yhot - frame_offset_topre
    #         #     gdk_pixbuf_composite(cursor_pixbuf, screenshot,
    #         #                         cursor_x, cursor_y,
    #         #                         rect.width, rect.height,
    #         #                         cursor_x, cursor_y,
    #         #                         1.0, 1.0,
    #         #                         GDK_INTERP_BILINEAR,
    #         #                         255)

    if options.enable_sound:
        play_sound_effect()
    # if options.enable_flash:
    #     screenshot_fallback_fire_flash(window, screenshot_coords)

    return screenshot


################### UTILS #####################

@async_function
def play_sound_effect():
    ctx = GSound.Context()
    ctx.init()
    ctx.play_simple({GSound.ATTR_EVENT_ID: "screen-capture"})
    GLib.usleep(2000000)

def capture_pixbuf(options):
    screenshot = None
    if options.enable_dbus_method:
        print("Capturing screenshot via GNOME Dbus...")
        screenshot = capture_via_gnome_dbus(options)
    if screenshot == None:
        print("Capturing screenshot via X11...")
        screenshot = capture_via_x11(options)
    return screenshot

def screenshot_show_dialog(parent, message_type, buttons_type, message, detail):
    dialog = Gtk.MessageDialog(parent, GTK_DIALOG_DESTROY_WITH_PARENT, message_type, buttons_type, message)
    dialog.set_title("")
    if detail != None:
        dialog.format_secondary_text(detail)

    if parent != None:
        group = parent.get_group()
        if group != None:
            group.add_window(dialog)

    response = dialog.run()
    dialog.destroy()
    return response
