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
kallithea.lib.feeds
~~~~~~~~~~~~~~~~~~~

Shared code for providing RSS and ATOM feeds.
"""

import datetime
import re

from webhelpers import feedgenerator


language = 'en-us'
ttl = "5"

class _Feeder(object):

    content_type = None
    feed_factory = None  # a webhelpers.feedgenerator

    @classmethod
    def render(cls, header, entries):
        feed = cls.feed_factory(
            language=language,
            ttl=ttl,  # rss only
            **header
        )
        for e in entries:
            feed.add_item(**e)
        return feed.writeString('utf-8')


class AtomFeed(_Feeder):

    content_type = 'application/atom+xml'

    feed_factory = feedgenerator.Atom1Feed


class RssFeed(_Feeder):

    content_type = 'application/rss+xml'

    feed_factory = feedgenerator.Rss201rev2Feed
