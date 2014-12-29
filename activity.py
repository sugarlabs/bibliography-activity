# Copyright 2014 Sam Parkinson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import json
import logging
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango

from sugar3.activity import activity
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.widgets import StopButton
from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from add_button import AddToolButton
from add_window import EntryWindow
from bib_types import ALL_TYPES, ALL_TYPE_NAMES
from main_list import MainList


class BibliographyActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self._has_read_file = False

        screen = Gdk.Screen.get_default()
        css_provider = Gtk.CssProvider.get_default()
        css_provider.load_from_path('style.css')
        context = Gtk.StyleContext()
        context.add_provider_for_screen(screen, css_provider,
                                        Gtk.STYLE_PROVIDER_PRIORITY_USER)

        toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()
        
        add_button = AddToolButton(ALL_TYPE_NAMES)
        add_button.connect('add-type', self.__add_type_cb)
        toolbar_box.toolbar.insert(add_button, -1)
        add_button.show()
   
        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()
        
        self._main_list = MainList()
        self._main_list.connect('edit-row', self.__edit_row_cb)
        self._main_list.connect('deleted-row', self.__deleted_row_cb)
        self._main_sw = Gtk.ScrolledWindow()
        self._main_sw.set_policy(Gtk.PolicyType.NEVER,
                                 Gtk.PolicyType.ALWAYS)
        self._main_sw.set_shadow_type(Gtk.ShadowType.NONE)
        self._main_sw.connect('key-press-event',
                              self.__key_press_event_cb)
        self._main_sw.add(self._main_list)
        self._main_list.show()

        self._empty_message = EmptyMessage()

        self._overlay = Gtk.Overlay()
        self._overlay.add(self._empty_message)
        self._empty_message.show()
        self.set_canvas(self._overlay)
        self._overlay.show()

    def add_item(self, text, type_, data):
        self._empty_message.hide()
        self._overlay.remove(self._overlay.get_child())
        self._overlay.add(self._main_sw)
        self._main_sw.show()
        self._main_list.show()
        self._main_list.add(text, type_, data)
        
    def __add_type_cb(self, add_button, type_):
        window = EntryWindow(ALL_TYPES[type_], self)
        window.connect('save-item', self.__save_item_cb)
        self._overlay.add_overlay(window)
        window.show()
    
    def __save_item_cb(self, window, *args):
        self.add_item(*args)
        window.hide()
        self._overlay.remove(window)

    def __edit_row_cb(self, tree_view, type_, json_string):
        previous_values = json.loads(json_string)
        window = EntryWindow(ALL_TYPES[type_], self, previous_values)
        window.connect('save-item', tree_view.edited_row_cb)
        self._overlay.add_overlay(window)
        window.show()

    def __deleted_row_cb(self, tree_view, *row):
        if len(tree_view.get_model()) == 0:
            self._main_list.hide()
            self._overlay.remove(self._overlay.get_child())
            self._overlay.add(self._empty_message)
            self._empty_message.show()

    def __key_press_event_cb(self, scrolled_window, event):
        keyname = Gdk.keyval_name(event.keyval)

        vadjustment = scrolled_window.props.vadjustment
        if keyname == 'Up':
            if vadjustment.props.value > vadjustment.props.lower:
                vadjustment.props.value -= vadjustment.props.step_increment
        elif keyname == 'Down':
            max_value = vadjustment.props.upper - vadjustment.props.page_size
            if vadjustment.props.value < max_value:
                vadjustment.props.value = min(
                    vadjustment.props.value + vadjustment.props.step_increment,
                    max_value)
        else:
            return False

    def write_file(self, file_path):
        data = self._main_list.json()
        with open(file_path, 'w') as f:
            json.dump(data, f)

        self.metadata['mime_type'] == 'application/json+bib'

    def read_file(self, file_path):
        # FIXME: Why does sugar call read_file so many times?
        if self._has_read_file:
            return
        self._has_read_file = True

        with open(file_path) as f:
            l = json.load(f)

        if len(l) > 0:
            self._main_list.load_json(l)
            self._empty_message.hide()
            self._overlay.remove(self._empty_message)
            self._overlay.add(self._main_sw)
            self._main_sw.show()
            self._main_list.show()


class EmptyMessage(Gtk.EventBox):

    def __init__(self):
        Gtk.EventBox.__init__(self)
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_WHITE.get_gdk_color())

        alignment = Gtk.Alignment.new(0.5, 0.5, 0.1, 0.1)
        self.add(alignment)

        box = Gtk.VBox()
        alignment.add(box)

        icon = Icon(pixel_size=style.LARGE_ICON_SIZE,
                    icon_name='view-list',
                    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                    fill_color=style.COLOR_BUTTON_GREY.get_svg())
        box.pack_start(icon, expand=True, fill=False, padding=0)

        label = Gtk.Label()
        color = style.COLOR_BUTTON_GREY.get_html()
        label.set_markup('<span weight="bold" color="%s">%s</span>' % (
            color, _('No Bibliography Entries')))
        box.pack_start(label, expand=True, fill=False, padding=0)

        self.show_all()
