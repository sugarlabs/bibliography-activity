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

import math
import json
import logging
from datetime import date
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton


SPECIAL_PLACEHOLDERS = {
    'datenow': lambda: '{:%d %B %Y}'.format(date.today())
}

def get_toplevel_size(toplevel):
    # Fixes a big where the window overflows on the XO
    screen = Gdk.Screen.get_default()
    return min(toplevel.get_allocated_width(), screen.width()), \
           min(toplevel.get_allocated_height(), screen.height())


class BaseWindow(Gtk.Box):
    '''
    A basic Sugar style popover window.
    Like view source mode.
    
    Use self to add content to a vbox.
    '''

    __gtype_name__ = 'BibliographyBaseWindow'
    
    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        self.props.halign = Gtk.Align.CENTER
        self.props.valign = Gtk.Align.CENTER

        self._tb = Gtk.Toolbar()
        self.pack_start(self._tb, False, True, 0)
        self._tb.show()

        sep = Gtk.SeparatorToolItem()
        sep.props.draw = False
        self._tb.insert(sep, -1)
        sep.show()

        label = Gtk.Label()
        label.set_markup('<b>{}</b>'.format(_('Edit Bibliography Entry')))
        label.set_alignment(0, 0.5)
        self._add_widget(label)

        sep = Gtk.SeparatorToolItem()
        sep.props.draw = False
        sep.props.expand = True
        self._tb.insert(sep, -1)
        sep.show()

        self.add_ = ToolButton(icon_name='dialog-ok')
        self.add_.set_tooltip(_('Add Bibliography Item'))
        self._tb.insert(self.add_, -1)
        self.add_.show()

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Close'))
        stop.connect('clicked', lambda *args: self.destroy())
        self._tb.insert(stop, -1)
        stop.show()

        self.show()

    def _add_widget(self, widget):
        t = Gtk.ToolItem()
        t.props.expand = True
        t.add(widget)
        widget.show()
        self._tb.insert(t, -1)
        t.show()


class EntryWindow(BaseWindow):
    
    __gsignals__ = {
        'save-item': (GObject.SIGNAL_RUN_FIRST, None, (str, str, str))
    }
    
    def __init__(self, bib_type, toplevel, previous_values=None):
        BaseWindow.__init__(self)
        self._type = bib_type

        eb = Gtk.EventBox()
        eb.get_style_context().add_class('window-event-box')
        self.pack_start(eb, True, True, 0)
        eb.show()

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        w, h = get_toplevel_size(toplevel)
        sw.set_size_request(w / 2, h / 4 * 3)
        eb.add(sw)
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
            if previous_values:
                entry.set_text(previous_values[i])
            self._text_entries.append(entry)

            start = math.floor(i / 2.0) * 3
            col = i % 2
            table.attach(label, col, col + 1, start, start + 1)
            table.attach(entry, col, col + 1, start + 1, start + 2)
            label.show()
            entry.show()

        self.add_.connect('clicked', self.__add_bib_cb)
    
    def __add_bib_cb(self, button):
        values = []
        for e in self._text_entries:
            values.append(e.get_text())
        result = self._type.format(map(GLib.markup_escape_text, values))
        
        self.emit('save-item', result, self._type.type, json.dumps(values))
