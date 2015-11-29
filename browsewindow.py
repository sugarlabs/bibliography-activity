# Copyright 2016 Sam Parkinson
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

import math
import json
import logging
from datetime import date
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import WebKit2

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.style import GRID_CELL_SIZE

from add_window import BaseWindow
from add_window import get_toplevel_size
from bib_types import WEB_TYPES, ALL_TYPES


class BrowseImportWindow(BaseWindow):
    '''
    A window that let's users import items from a browse activity

    Args:
        data (dict): JSON decoded browse activity data
        toplevel (Gtk.Window): toplevel window
    '''

    # TODO:  Port to GObject.Signal
    __gsignals__ = {
        'save-item': (GObject.SIGNAL_RUN_FIRST, None, (str, str, str))
    }

    def __init__(self, data, toplevel):
        BaseWindow.__init__(self)
        self._toplevel = toplevel

        print('Browse window with', data)
        self._links = data.get('shared_links', [])
        if not self._links:
            self._show_howto_copy()
            return

        self._total_links = len(self._links)
        self._entry = None

        self._paned = Gtk.Paned()
        self.add(self._paned)
        w, h = get_toplevel_size(toplevel)
        self._paned.set_size_request(w - (2*GRID_CELL_SIZE), h / 4 * 3)
        self._paned.show()

        self._webview = WebKit2.WebView()
        self._paned.add1(self._webview)
        self._webview.set_size_request(w / 2, h / 4 * 3)
        self._webview.show()

        self._2box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._paned.add2(self._2box)
        self._2box.show()

        self._combo = Gtk.ComboBoxText()
        for t in WEB_TYPES:
            self._combo.append(t.type, t.name)
        self._combo.set_active(0)
        self._combo.connect('changed', self.__combo_changed_cb)
        self._2box.add(self._combo)
        self._combo.show()

        self.next_link()
        self.add_.connect('clicked', self.__add_clicked_cb)

    def _show_howto_copy(self):
        self.label.set_markup('<b>Learn to Bookmark in Browse</b>')
        self.add_.connect('clicked', lambda *args: self.destroy())

    def next_link(self):
        '''
        Show the next link from the data to the user
        '''
        if len(self._links) == 0:
            self.destroy()
            return
        self._link = self._links.pop(0)

        label = ('  <span bgcolor="#fff" color="#282828" size="x-large"'
                  '>{}/{}</span> {}').format(
            self._total_links - len(self._links),
            self._total_links,
            self._link.get('title', _('Untitled')))
        self.label.set_markup(label)

        self._webview.load_uri(self._link.get('url'))

        id_ = self._combo.get_active_id()
        bib_type = ALL_TYPES[id_]
        self._set_entry(bib_type)

    def _set_entry(self, type_):
        if self._entry is not None:
            self._entry.hide()
            self._2box.remove(self._entry)
            self._entry.destroy()

        self._entry = EntryWidget(
            type_,
            self._toplevel,
            timestamp=self._link.get('timestamp'),
            title=self._link.get('title'),
            uri=self._link.get('url'))
        self._2box.pack_start(self._entry, True, True, 0)
        self._entry.show()

    def __add_clicked_cb(self, button):
        self.emit('save-item', *self._entry.get_data())
        self.next_link()

    def __combo_changed_cb(self, combo):
        id_ = combo.get_active_id()
        bib_type = ALL_TYPES[id_]
        self._set_entry(bib_type)


# FIXME:  Get rid of copy and paste code reuse from EntryWindow

SPECIAL_PLACEHOLDERS = {
    'datenow': lambda: '{:%d %B %Y}'.format(date.today())
}

class EntryWidget(Gtk.EventBox):
    '''
    A widget that lets the user compose a bibliography item, using
    a pre built template/formatter.

    Args:
        bib_type (BibType): the type of item the user will add
        toplevel (Gtk.Window): top level window that this will be added to
        previous_values (list):  Values to use when updating the entry
        timestamp (int): timestamp to use in a website template
        title (str): title to use in a website template
        uri (str): uri to use in a website template
    '''
    
    def __init__(self, bib_type, toplevel, previous_values=None,
                 timestamp=None, title=None, uri=None):
        Gtk.EventBox.__init__(self)
        self._type = bib_type
        self.get_style_context().add_class('window-event-box')

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(sw)
        sw.show()

        alignment = Gtk.Alignment()
        alignment.set_padding(6, 6, 6, 6)
        sw.add(alignment)
        alignment.show()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        alignment.add(box)
        box.show()
        
        example = Gtk.Label()
        markup = '<b> {} Reference List Example: </b>\n{}'.format(
            self._type.name,
            self._type.format([(SPECIAL_PLACEHOLDERS[i[1:]]() \
                                if i.startswith('*') else i) \
                              for _, i in self._type.items]))
        example.set_markup(markup)
        example.props.wrap = True
        example.props.max_width_chars = \
            (get_toplevel_size(toplevel)[0] / 2) / 18
        box.add(example)
        example.show()
        
        table = Gtk.Table(int(math.ceil(len(self._type.items)/2.0) * 3) - 1,
                          2, True)
        table.props.column_spacing = 6
        box.add(table)
        table.show()

        self._text_entries = []
        for i, v in enumerate(self._type.items):
            text, placeholder = v
            label = Gtk.Label(text)
            entry = Gtk.Entry()

            if placeholder.startswith('*'):
                entry.set_text(SPECIAL_PLACEHOLDERS[placeholder[1:]]())
            else:
                entry.set_placeholder_text(placeholder)
            if placeholder == '*datenow' and timestamp is not None:
               entry.set_text('{:%d %B %Y}'.format(
                    date.fromtimestamp(timestamp)))
            if i == self._type.web_title_index and title is not None:
                entry.set_text(title)
            if i == self._type.web_uri_index and uri is not None:
                entry.set_text(uri)
            if previous_values:
                entry.set_text(previous_values[i])
            self._text_entries.append(entry)

            start = math.floor(i / 2.0) * 3
            col = i % 2
            table.attach(label, col, col + 1, start, start + 1)
            table.attach(entry, col, col + 1, start + 1, start + 2)
            label.show()
            entry.show()
    
    def get_data(self):
        '''
        Returns the state of the entry window as a tuple of:

        * String of markup
        * Type name (`BibType.type`)
        * JSON dump of the values (good for use with `previous_values`)
        '''
        values = []
        for e in self._text_entries:
            values.append(e.get_text())
        result = self._type.format(map(GLib.markup_escape_text, values))
        
        return (result, self._type.type, json.dumps(values))
