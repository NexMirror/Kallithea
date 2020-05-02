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

import paginate
import paginate_sqlalchemy
import sqlalchemy.orm
from webhelpers2.html import literal

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

    def pager(self):
        return literal(
            paginate.Page.pager(self,
                format='<ul class="pagination">$link_previous\n~4~$link_next</ul>',
                link_attr={'class': 'pager_link'},
                dotdot_attr={'class': 'pager_dotdot'},
                separator='\n',
                ))

    @staticmethod
    def default_link_tag(item):
        # based on the base class implementation, but wrapping results in <li>, and with different handling of current_page
        text = item['value']
        if item['type'] == 'current_page':  # we need active on the li and can thus not use curpage_attr
            return '''<li class="active"><span>%s</span></li>''' % text

        if not item['href'] or item['type'] == 'span':
            if item['attrs']:
                text = paginate.make_html_tag('span', **item['attrs']) + text + '</span>'
        else:
            target_url = item['href']
            text =  paginate.make_html_tag('a', text=text, href=target_url, **item['attrs'])
        return '''<li>%s</li>''' % text
