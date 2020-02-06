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

import mako.template


language = 'en-us'
ttl = "5"


# From ``django.utils.feedgenerator`` via webhelpers.feedgenerator
def rfc2822_date(date):
    # We do this ourselves to be timezone aware, email.Utils is not tz aware.
    if getattr(date, "tzinfo", False):
        time_str = date.strftime('%a, %d %b %Y %H:%M:%S ')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d%02d" % (hour, minute)
    else:
        return date.strftime('%a, %d %b %Y %H:%M:%S -0000')

# From ``django.utils.feedgenerator`` via webhelpers.feedgenerator
def rfc3339_date(date):
    if getattr(date, "tzinfo", False):
        time_str = date.strftime('%Y-%m-%dT%H:%M:%S')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d:%02d" % (hour, minute)
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

# From ``django.utils.feedgenerator`` via webhelpers.feedgenerator
def get_tag_uri(url, date):
    "Creates a TagURI. See http://diveintomark.org/archives/2004/05/28/howto-atom-id"
    tag = re.sub('^http://', '', url)
    if date is not None:
        tag = re.sub('/', ',%s:/' % date.strftime('%Y-%m-%d'), tag, 1)
    tag = re.sub('#', '/', tag)
    return 'tag:' + tag


class Attributes(object):
    """Simple namespace for attribute dict access in mako and elsewhere"""
    def __init__(self, a_dict):
        self.__dict__ = a_dict


class _Feeder(object):

    content_type = None
    template = None  # subclass must provide a mako.template.Template

    @classmethod
    def render(cls, header, entries):
        try:
            latest_pubdate = max(
                pubdate for pubdate in (e.get('pubdate') for e in entries)
                if pubdate
            )
        except ValueError:  # max() arg is an empty sequence ... or worse
            latest_pubdate = datetime.datetime.now()

        return cls.template.render(
            language=language,
            ttl=ttl,  # rss only
            latest_pubdate=latest_pubdate,
            rfc2822_date=rfc2822_date,  # for RSS
            rfc3339_date=rfc3339_date,  # for Atom
            get_tag_uri=get_tag_uri,
            entries=[Attributes(e) for e in entries],
            **header
        )


class AtomFeed(_Feeder):

    content_type = 'application/atom+xml'

    template = mako.template.Template('''\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="${language}">
  <title>${title}</title>
  <link href="${link}" rel="alternate"></link>
  <id>${link}</id>
  <updated>${rfc3339_date(latest_pubdate)}</updated>
  % for entry in entries:
  <entry>
    <title>${entry.title}</title>
    <link href="${entry.link}" rel="alternate"></link>
    <updated>${rfc3339_date(entry.pubdate)}</updated>
    <published>${rfc3339_date(entry.pubdate)}</published>
    <author>
      <name>${entry.author_name}</name>
      <email>${entry.author_email}</email>
    </author>
    <id>${get_tag_uri(entry.link, entry.pubdate)}</id>
    <summary type="html">${entry.description}</summary>
  </entry>
  % endfor
</feed>
''', default_filters=['x'], output_encoding='utf-8', encoding_errors='replace')


class RssFeed(_Feeder):

    content_type = 'application/rss+xml'

    template = mako.template.Template('''\
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>${title}</title>
    <link>${link}</link>
    <description>${description}</description>
    <language>${language}</language>
    <lastBuildDate>${rfc2822_date(latest_pubdate)}</lastBuildDate>
    <ttl>${ttl}</ttl>
    % for entry in entries:
    <item>
      <title>${entry.title}</title>
      <link>${entry.link}</link>
      <description>${entry.description}</description>
      <author>${entry.author_email} (${entry.author_name})</author>
      <pubDate>${rfc2822_date(entry.pubdate)}</pubDate>
    </item>
    % endfor
  </channel>
</rss>
''', default_filters=['x'], output_encoding='utf-8', encoding_errors='replace')
