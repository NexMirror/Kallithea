# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Custom paging classes
"""
import logging
import re

import paginate
import paginate_sqlalchemy
import sqlalchemy.orm
from webhelpers2.html import HTML, literal

from kallithea.config.routing import url


log = logging.getLogger(__name__)


class Page(paginate.Page):

    def __init__(self, collection,
                 page=1, items_per_page=20, item_count=None,
                 **kwargs):
        if isinstance(collection, sqlalchemy.orm.query.Query):
            collection = paginate_sqlalchemy.SqlalchemyOrmWrapper(collection)
        paginate.Page.__init__(self, collection, page=page, items_per_page=items_per_page, item_count=item_count,
                               url_maker=lambda page: url.current(page=page, **kwargs))

    def _pagerlink(self, page, text):
        """hack to mimic old webhelpers.paginate internals"""
        return literal('''<li><a class="pager_link" href="%s">%s</a></li>''') % (self.url_maker(page), text)

    def _get_pos(self, cur_page, max_page, items):
        edge = (items / 2) + 1
        if (cur_page <= edge):
            radius = max(items / 2, items - cur_page)
        elif (max_page - cur_page) < edge:
            radius = (items - 1) - (max_page - cur_page)
        else:
            radius = items / 2

        left = max(1, (cur_page - (radius)))
        right = min(max_page, cur_page + (radius))
        return left, cur_page, right

    def _range(self, regexp_match):
        """
        Return range of linked pages (e.g. '1 2 [3] 4 5 6 7 8').

        Arguments:

        regexp_match
            A "re" (regular expressions) match object containing the
            radius of linked pages around the current page in
            regexp_match.group(1) as a string

        This function is supposed to be called as a callable in
        re.sub.

        """
        radius = int(regexp_match.group(1))

        # Compute the first and last page number within the radius
        # e.g. '1 .. 5 6 [7] 8 9 .. 12'
        # -> leftmost_page  = 5
        # -> rightmost_page = 9
        leftmost_page, _cur, rightmost_page = self._get_pos(self.page,
                                                            self.last_page,
                                                            (radius * 2) + 1)
        nav_items = []

        # Create a link to the first page (unless we are on the first page
        # or there would be no need to insert '..' spacers)
        if self.page != self.first_page and self.first_page < leftmost_page:
            nav_items.append(HTML.li(self._pagerlink(self.first_page, self.first_page)))

        # Insert dots if there are pages between the first page
        # and the currently displayed page range
        if leftmost_page - self.first_page > 1:
            # Wrap in a SPAN tag if nolink_attr is set
            text_ = '..'
            if self.dotdot_attr:
                text_ = HTML.span(c=text_, **self.dotdot_attr)
            nav_items.append(HTML.li(text_))

        for thispage in xrange(leftmost_page, rightmost_page + 1):
            # Highlight the current page number and do not use a link
            text_ = str(thispage)
            if thispage == self.page:
                # Wrap in a SPAN tag if nolink_attr is set
                if self.curpage_attr:
                    text_ = HTML.li(HTML.span(c=text_), **self.curpage_attr)
                nav_items.append(text_)
            # Otherwise create just a link to that page
            else:
                nav_items.append(HTML.li(self._pagerlink(thispage, text_)))

        # Insert dots if there are pages between the displayed
        # page numbers and the end of the page range
        if self.last_page - rightmost_page > 1:
            text_ = '..'
            # Wrap in a SPAN tag if nolink_attr is set
            if self.dotdot_attr:
                text_ = HTML.span(c=text_, **self.dotdot_attr)
            nav_items.append(HTML.li(text_))

        # Create a link to the very last page (unless we are on the last
        # page or there would be no need to insert '..' spacers)
        if self.page != self.last_page and rightmost_page < self.last_page:
            nav_items.append(HTML.li(self._pagerlink(self.last_page, self.last_page)))

        #_page_link = url.current()
        #nav_items.append(literal('<link rel="prerender" href="%s?page=%s">' % (_page_link, str(int(self.page)+1))))
        #nav_items.append(literal('<link rel="prefetch" href="%s?page=%s">' % (_page_link, str(int(self.page)+1))))
        return self.separator.join(nav_items)

    def pager(self, format='<ul class="pagination">$link_previous ~2~ $link_next</ul>', page_param='page', partial_param='partial',
        show_if_single_page=False, separator=' ', onclick=None,
        symbol_first='<<', symbol_last='>>',
        symbol_previous='<', symbol_next='>',
        link_attr=None,
        curpage_attr=None,
        dotdot_attr=None, **kwargs
    ):
        self.curpage_attr = curpage_attr or {'class': 'active'}
        self.separator = separator
        self.pager_kwargs = kwargs
        self.page_param = page_param
        self.partial_param = partial_param
        self.onclick = onclick
        self.link_attr = link_attr or {'class': 'pager_link', 'rel': 'prerender'}
        self.dotdot_attr = dotdot_attr or {'class': 'pager_dotdot'}

        # Don't show navigator if there is no more than one page
        if self.page_count == 0 or (self.page_count == 1 and not show_if_single_page):
            return ''

        from string import Template
        # Replace ~...~ in token format by range of pages
        result = re.sub(r'~(\d+)~', self._range, format)

        # Interpolate '%' variables
        result = Template(result).safe_substitute({
            'first_page': self.first_page,
            'last_page': self.last_page,
            'page': self.page,
            'page_count': self.page_count,
            'items_per_page': self.items_per_page,
            'first_item': self.first_item,
            'last_item': self.last_item,
            'item_count': self.item_count,
            'link_first': self.page > self.first_page and
                    self._pagerlink(self.first_page, symbol_first) or '',
            'link_last': self.page < self.last_page and
                    self._pagerlink(self.last_page, symbol_last) or '',
            'link_previous': HTML.li(self.previous_page and
                    self._pagerlink(self.previous_page, symbol_previous)
                    or HTML.a(symbol_previous)),
            'link_next': HTML.li(self.next_page and
                    self._pagerlink(self.next_page, symbol_next)
                    or HTML.a(symbol_next)),
        })

        return literal(result)
