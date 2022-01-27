#!/usr/bin/python3

import os
import sys
import gi
from gi.repository import Gtk

########### SHELL #########################3333

def shell_get_pixbuf(rect):
    path = os.path.join(GLib.get_user_cache_dir(), "gnome-screenshot")
    g_mkdir_with_parents(path, 0700)

    tmpname = g_strdup_printf("scr-%d.png", GLib.random_int())
    filename = os.path.join(path, tmpname)

    if screenshot_config.take_window_shot:
        method_name = "ScreenshotWindow"
        method_params = g_variant_new("(bbbs)",
                                     True,
                                     screenshot_config.include_pointer,
                                     True, /* flash */
                                     filename)
    elif rectangle != None:
        method_name = "ScreenshotArea"
        method_params = g_variant_new("(iiiibs)",
                                     rectangle.x, rectangle.y,
                                     rectangle.width, rectangle.height,
                                     True, /* flash */
                                     filename)
    else:
        method_name = "Screenshot"
        method_params = g_variant_new("(bbs)",
                                     screenshot_config.include_pointer,
                                     True, /* flash */
                                     filename)

    connection = g_application_get_dbus_connection(g_application_get_default())
    g_dbus_connection_call_sync(connection,
                               "org.gnome.Shell.Screenshot",
                               "/org/gnome/Shell/Screenshot",
                               "org.gnome.Shell.Screenshot",
                               method_name,
                               method_params,
                               None,
                               G_DBUS_CALL_FLAGS_NONE,
                               -1,
                               None,
                               &error)

    if error == None:
        screenshot = gdk_pixbuf_new_from_file(filename, &error)

        # remove the temporary file created by the shell
        g_unlink(filename)

############# X11 ############################33


def find_wm_window(window):

    if window == Gdk.get_default_root_window():
        return None

    xid = GDK_WINDOW_XID(window)

    while True:
        if XQueryTree(Gdk.Display.get_default(), xid, &root, &parent, &children, &nchildren) == 0:
            print("Couldn't find window manager window")
            return None

        if root == parent:
            return xid

        xid = parent

def make_region_with_monitors(display):
    num_monitors = Gdk.Display.get_n_monitors()
    region = cairo.Region()

    for i in range(num_monitors):
        monitor = Gdk.Display.get_monitor(i)
        rect = monitor.get_geometry()
        rect = region.union_rectangle()

    return region


def blank_rectangle_in_pixbuf(pixbuf, rect):
    x2 = rect.x + rect.width
    y2 = rect.y + rect.height
    pixels = pixbuf.get_pixels()
    rowstride = pixbuf.get_rowstride()
    has_alpha = pixbuf.get_has_alpha()
    n_channels = pixbuf.get_n_channels()

    for y in range(rect.y, y2):
        row = pixels + y * rowstride
        p = row + rect.x * n_channels

        for x in range(rect.x, x2):
            *p++ = 0
            *p++ = 0
            *p++ = 0

            if has_alpha:
                *p++ = 255 # opaque black

def blank_region_in_pixbuf(pixbuf, region):
    n_rects = region.num_rectangles()
    pixbuf_rect.x = 0
    pixbuf_rect.y = 0
    pixbuf_rect.width = pixbuf.get_width()
    pixbuf_rect.height = pixbuf.get_height()

    for i in range(n_rects):
        rect = region.get_rectangle(i)
        if rect.intersect(pixbuf_rect, dest):
            blank_rectangle_in_pixbuf(pixbuf, &dest)


# When there are multiple monitors with different resolutions, the visible area
# within the root window may not be rectangular(it may have an L-shape, for
# example).  In that case, mask out the areas of the root window which would
# not be visible in the monitors, so that screenshot do not end up with content
# that the user won't ever see.
def mask_monitors(pixbuf, root_window):
    display = root_window.get_display()
    region_with_monitors = make_region_with_monitors(display)
    rect.x = 0
    rect.y = 0
    rect.width = pixbuf.get_width()
    rect.height = pixbuf.get_height()

    invisible_region = cairo_region_create_rectangle(&rect)
    cairo_region_subtract(invisible_region, region_with_monitors)
    blank_region_in_pixbuf(pixbuf, invisible_region)
    cairo_region_destroy(region_with_monitors)
    cairo_region_destroy(invisible_region)

def screenshot_fallback_get_window_rect_coords(window, real_coordinates_out, screenshot_coordinates_out):
    real_coordinates = window.get_frame_extents()
    x_orig = real_coordinates.x
    y_orig = real_coordinates.y
    width  = real_coordinates.width
    height = real_coordinates.height

    if real_coordinates_out != None:
        real_coordinates_out = real_coordinates

    if x_orig < 0:
        width = width + x_orig
        x_orig = 0

    if y_orig < 0:
        height = height + y_orig
        y_orig = 0

    if x_orig + width > gdk_screen_width():
        width = gdk_screen_width() - x_orig

    if y_orig + height > gdk_screen_height():
        height = gdk_screen_height() - y_orig

    if screenshot_coordinates_out != None:
        screenshot_coordinates_out.x = x_orig
        screenshot_coordinates_out.y = y_orig
        screenshot_coordinates_out.width = width
        screenshot_coordinates_out.height = height

def screenshot_fallback_fire_flash(window, rectangle):
    if rectangle == None:
        rectangle = screenshot_fallback_get_window_rect_coords(window, None)
    flash = cheese_flash_new()
    flash.fire(rect)


def do_find_current_window():
    current_window = Gdk.Screen.get_default().get_active_window()
    seat = Gdk.Display.get_default().get_default_seat()
    device = seat.get_pointer()

    # If there's no active window, we fall back to returning the
    # window that the cursor is in.
    if current_window == None:
        current_window = gdk_device_get_window_at_position(device, None, None)

    if current_window != None:
        if current_window == Gdk.get_default_root_window()
        or current_window.get_type_hint() == GDK_WINDOW_TYPE_HINT_DESKTOP:
            # if the current window is the desktop(e.g. nautilus), we
            # return None, as getting the whole screen makes more sense.
            return None

        # Once we have a window, we take the toplevel ancestor.
        current_window = current_window.get_toplevel()

    return current_window

def screenshot_fallback_find_current_window():
    window = None
    if screenshot_config.take_window_shot:
        window = do_find_current_window()
        if window == None:
            screenshot_config.take_window_shot = False

    if window == None
        window = Gdk.get_default_root_window()

    return window


def screenshot_backend_x11_get_pixbuf(rectangle):
    frame_offset = { 0, 0, 0, 0 }
    window = screenshot_fallback_find_current_window()
    screenshot_fallback_get_window_rect_coords(window,
                                              &real_coords,
                                              &screenshot_coords)

    wm = find_wm_window(window)
    if wm != None:
        wm_window = gdk_x11_window_foreign_new_for_display(window.get_display(), wm)

        screenshot_fallback_get_window_rect_coords(wm_window,
                                                  &wm_real_coords,
                                                  None)

        frame_offset.left =(gdouble)(real_coords.x - wm_real_coords.x)
        frame_offset.top =(gdouble)(real_coords.y - wm_real_coords.y)
        frame_offset.right =(gdouble)(wm_real_coords.width - real_coords.width - frame_offset.left)
        frame_offset.bottom =(gdouble)(wm_real_coords.height - real_coords.height - frame_offset.top)

    if rectangle:
        screenshot_coords.x = rectangle.x - screenshot_coords.x
        screenshot_coords.y = rectangle.y - screenshot_coords.y
        screenshot_coords.width  = rectangle.width
        screenshot_coords.height = rectangle.height

    root = Gdk.get_default_root_window()
    screenshot = gdk_pixbuf_get_from_window(root,
                                           screenshot_coords.x, screenshot_coords.y,
                                           screenshot_coords.width, screenshot_coords.height)

    if not (screenshot_config.take_window_shot or screenshot_config.take_area_shot):
        mask_monitors(screenshot, root)

    if wm != None:
        # we must use XShape to avoid showing what's under the rounder corners
        # of the WM decoration.
        rectangles = XShapeGetRectangles(Gdk.Display.XDISPLAY(Gdk.Display.get_default()),
                                        wm,
                                        ShapeBounding,
                                        &rectangle_count,
                                        &rectangle_order)
        if rectangles and rectangle_count > 0:
            int scale_factor = gdk_window_get_scale_factor(wm_window)
            gboolean has_alpha = gdk_pixbuf_get_has_alpha(screenshot)
            GdkPixbuf *tmp = gdk_pixbuf_new(GDK_COLORSPACE_RGB, True, 8,
                                           gdk_pixbuf_get_width(screenshot),
                                           gdk_pixbuf_get_height(screenshot))
            gdk_pixbuf_fill(tmp, 0)

            for i in range(rectangle_count):
                # If we're using invisible borders, the ShapeBounding might not
                # have the same size as the frame extents, as it would include the
                # areas for the invisible borders themselves.
                # In that case, trim every rectangle we get by the offset between the
                # WM window size and the frame extents.
                # Note that the XShape values are in actual pixels, whereas the GDK
                # ones are in display pixels(i.e. scaled), so we need to apply the
                # scale factor to the former to use display pixels for all our math.
                rec_x = rectangles[i].x / scale_factor
                rec_y = rectangles[i].y / scale_factor
                rec_width = rectangles[i].width / scale_factor -(frame_offset.left + frame_offset.right)
                rec_height = rectangles[i].height / scale_factor -(frame_offset.top + frame_offset.bottom)

                if(real_coords.x < 0):
                    rec_x += real_coords.x
                    rec_x = MAX(rec_x, 0)
                    rec_width += real_coords.x

                if(real_coords.y < 0):
                    rec_y += real_coords.y
                    rec_y = MAX(rec_y, 0)
                    rec_height += real_coords.y

                if(screenshot_coords.x + rec_x + rec_width > gdk_screen_width()):
                    rec_width = gdk_screen_width() - screenshot_coords.x - rec_x

                if(screenshot_coords.y + rec_y + rec_height > gdk_screen_height()):
                    rec_height = gdk_screen_height() - screenshot_coords.y - rec_y

                # Undo the scale factor in order to copy the pixbuf data pixel-wise
                for y in range(rec_y * scale_factor, (rec_y + rec_height) * scale_factor):
                    src_pixels = screenshot.get_pixels()
                             + y * screenshot.get_rowstride()
                             + rec_x * scale_factor *(has_alpha ? 4 : 3)
                    dest_pixels = tmp.get_pixels()
                              + y * tmp.get_rowstride()
                              + rec_x * scale_factor * 4

                    for x in range(rec_width * scale_factor):
                        *dest_pixels++ = *src_pixels++
                        *dest_pixels++ = *src_pixels++
                        *dest_pixels++ = *src_pixels++

                        if(has_alpha)
                            *dest_pixels++ = *src_pixels++
                        else
                            *dest_pixels++ = 255

            g_set_object(&screenshot, tmp)

            XFree(rectangles)

    # if we have a selected area, there were by definition no cursor in the screenshot
    if(screenshot_config.include_pointer && !rectangle):
        g_autoptr(GdkCursor) cursor = None
        g_autoptr(GdkPixbuf) cursor_pixbuf = None

        cursor = gdk_cursor_new_for_display(Gdk.Display.get_default(), GDK_LEFT_PTR)
        cursor_pixbuf = gdk_cursor_get_image(cursor)

        if(cursor_pixbuf != None):
            seat = Gdk.Display.get_default_seat(Gdk.Display.get_default())
            device = gdk_seat_get_pointer(seat)

            if(wm_window != None):
                gdk_window_get_device_position(wm_window, device,
                                            &cx, &cy, None)
            else:
                gdk_window_get_device_position(window, device,
                                            &cx, &cy, None)

            sscanf(gdk_pixbuf_get_option(cursor_pixbuf, "x_hot"), "%d", &xhot)
            sscanf(gdk_pixbuf_get_option(cursor_pixbuf, "y_hot"), "%d", &yhot)

            # in rect we have the cursor window coordinates
            rect.x = cx + real_coords.x
            rect.y = cy + real_coords.y
            rect.width = gdk_pixbuf_get_width(cursor_pixbuf)
            rect.height = gdk_pixbuf_get_height(cursor_pixbuf)

            # see if the pointer is inside the window
            if(gdk_rectangle_intersect(&real_coords, &rect, &rect)):
                cursor_x = cx - xhot - frame_offset.left
                cursor_y = cy - yhot - frame_offset.top
                gdk_pixbuf_composite(cursor_pixbuf, screenshot,
                                    cursor_x, cursor_y,
                                    rect.width, rect.height,
                                    cursor_x, cursor_y,
                                    1.0, 1.0,
                                    GDK_INTERP_BILINEAR,
                                    255)

    screenshot_fallback_fire_flash(window, rectangle)

    return screenshot


################### UTILS #####################

def screenshot_play_sound_effect(event_id, event_desc):
    c = ca_gtk_context_get()
    res = ca_proplist_create(&p)
    if res < 0:
        goto done

    res = ca_proplist_sets(p, CA_PROP_EVENT_ID, event_id)
    if res < 0:
        goto done

    res = ca_proplist_sets(p, CA_PROP_EVENT_DESCRIPTION, event_desc)
    if res < 0:
        goto done

    res = ca_proplist_sets(p, CA_PROP_CANBERRA_CACHE_CONTROL, "permanent")
    if res < 0:
        goto done

    ca_context_play_full(c, 0, p, None, None)

    done:
        if(p != None)
            ca_proplist_destroy(p)

def screenshot_get_pixbuf(rectangle):
    screenshot = screenshot_shell_get_pixbuf(rectangle)
    if screenshot == None:
        g_message("Unable to use GNOME's interface, falling back to X11 method")
        screenshot = screenshot_x11_get_pixbuf(rectangle)
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
