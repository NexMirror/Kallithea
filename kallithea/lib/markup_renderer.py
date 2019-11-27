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
kallithea.lib.markup_renderer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Renderer for markup languages with ability to parse using rst or markdown

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Oct 27, 2011
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import re
import traceback

import bleach
import markdown as markdown_mod

from kallithea.lib.utils2 import MENTIONS_REGEX, safe_unicode


log = logging.getLogger(__name__)


url_re = re.compile(r'''\bhttps?://(?:[\da-zA-Z0-9@:.-]+)'''
                    r'''(?:[/a-zA-Z0-9_=@#~&+%.,:;?!*()-]*[/a-zA-Z0-9_=@#~])?''')


class MarkupRenderer(object):
    RESTRUCTUREDTEXT_DISALLOWED_DIRECTIVES = ['include', 'meta', 'raw']

    MARKDOWN_PAT = re.compile(r'md|mkdn?|mdown|markdown', re.IGNORECASE)
    RST_PAT = re.compile(r're?st', re.IGNORECASE)
    PLAIN_PAT = re.compile(r'readme', re.IGNORECASE)

    @classmethod
    def _detect_renderer(cls, source, filename):
        """
        runs detection of what renderer should be used for generating html
        from a markup language

        filename can be also explicitly a renderer name
        """

        if cls.MARKDOWN_PAT.findall(filename):
            return cls.markdown
        elif cls.RST_PAT.findall(filename):
            return cls.rst
        elif cls.PLAIN_PAT.findall(filename):
            return cls.rst
        return cls.plain

    @classmethod
    def _flavored_markdown(cls, text):
        """
        Github style flavored markdown

        :param text:
        """
        from hashlib import md5

        # Extract pre blocks.
        extractions = {}

        def pre_extraction_callback(matchobj):
            digest = md5(matchobj.group(0)).hexdigest()
            extractions[digest] = matchobj.group(0)
            return "{gfm-extraction-%s}" % digest
        pattern = re.compile(r'<pre>.*?</pre>', re.MULTILINE | re.DOTALL)
        text = re.sub(pattern, pre_extraction_callback, text)

        # Prevent foo_bar_baz from ending up with an italic word in the middle.
        def italic_callback(matchobj):
            s = matchobj.group(0)
            if list(s).count('_') >= 2:
                return s.replace('_', r'\_')
            return s
        text = re.sub(r'^(?! {4}|\t)\w+_\w+_\w[\w_]*', italic_callback, text)

        # In very clear cases, let newlines become <br /> tags.
        def newline_callback(matchobj):
            if len(matchobj.group(1)) == 1:
                return matchobj.group(0).rstrip() + '  \n'
            else:
                return matchobj.group(0)
        pattern = re.compile(r'^[\w\<][^\n]*(\n+)', re.MULTILINE)
        text = re.sub(pattern, newline_callback, text)

        # Insert pre block extractions.
        def pre_insert_callback(matchobj):
            return '\n\n' + extractions[matchobj.group(1)]
        text = re.sub(r'{gfm-extraction-([0-9a-f]{32})\}',
                      pre_insert_callback, text)

        return text

    @classmethod
    def render(cls, source, filename=None):
        """
        Renders a given filename using detected renderer
        it detects renderers based on file extension or mimetype.
        At last it will just do a simple html replacing new lines with <br/>

        >>> MarkupRenderer.render('''<img id="a" style="margin-top:-1000px;color:red" src="http://example.com/test.jpg">''', '.md')
        u'<p><img id="a" src="http://example.com/test.jpg" style="color: red;"></p>'
        >>> MarkupRenderer.render('''<img class="c d" src="file://localhost/test.jpg">''', 'b.mkd')
        u'<p><img class="c d"></p>'
        >>> MarkupRenderer.render('''<a href="foo">foo</a>''', 'c.mkdn')
        u'<p><a href="foo">foo</a></p>'
        >>> MarkupRenderer.render('''<script>alert(1)</script>''', 'd.mdown')
        u'&lt;script&gt;alert(1)&lt;/script&gt;'
        >>> MarkupRenderer.render('''<div onclick="alert(2)">yo</div>''', 'markdown')
        u'<div>yo</div>'
        >>> MarkupRenderer.render('''<a href="javascript:alert(3)">yo</a>''', 'md')
        u'<p><a>yo</a></p>'
        """

        renderer = cls._detect_renderer(source, filename)
        readme_data = renderer(source)
        # Allow most HTML, while preventing XSS issues:
        # no <script> tags, no onclick attributes, no javascript
        # "protocol", and also limit styling to prevent defacing.
        return bleach.clean(readme_data,
            tags=['a', 'abbr', 'b', 'blockquote', 'br', 'code', 'dd',
                  'div', 'dl', 'dt', 'em', 'h1', 'h2', 'h3', 'h4', 'h5',
                  'h6', 'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'span',
                  'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th',
                  'thead', 'tr', 'ul'],
            attributes=['class', 'id', 'style', 'label', 'title', 'alt', 'href', 'src'],
            styles=['color'],
            protocols=['http', 'https', 'mailto'],
            )

    @classmethod
    def plain(cls, source, universal_newline=True):
        source = safe_unicode(source)
        if universal_newline:
            newline = '\n'
            source = newline.join(source.splitlines())

        def url_func(match_obj):
            url_full = match_obj.group(0)
            return '<a href="%(url)s">%(url)s</a>' % ({'url': url_full})
        source = url_re.sub(url_func, source)
        return '<br />' + source.replace("\n", '<br />')

    @classmethod
    def markdown(cls, source, safe=True, flavored=False):
        """
        Convert Markdown (possibly GitHub Flavored) to INSECURE HTML, possibly
        with "safe" fall-back to plaintext. Output from this method should be sanitized before use.

        >>> MarkupRenderer.markdown('''<img id="a" style="margin-top:-1000px;color:red" src="http://example.com/test.jpg">''')
        u'<p><img id="a" style="margin-top:-1000px;color:red" src="http://example.com/test.jpg"></p>'
        >>> MarkupRenderer.markdown('''<img class="c d" src="file://localhost/test.jpg">''')
        u'<p><img class="c d" src="file://localhost/test.jpg"></p>'
        >>> MarkupRenderer.markdown('''<a href="foo">foo</a>''')
        u'<p><a href="foo">foo</a></p>'
        >>> MarkupRenderer.markdown('''<script>alert(1)</script>''')
        u'<script>alert(1)</script>'
        >>> MarkupRenderer.markdown('''<div onclick="alert(2)">yo</div>''')
        u'<div onclick="alert(2)">yo</div>'
        >>> MarkupRenderer.markdown('''<a href="javascript:alert(3)">yo</a>''')
        u'<p><a href="javascript:alert(3)">yo</a></p>'
        >>> MarkupRenderer.markdown('''## Foo''')
        u'<h2>Foo</h2>'
        >>> print MarkupRenderer.markdown('''
        ...     #!/bin/bash
        ...     echo "hello"
        ... ''')
        <table class="code-highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1
        2</pre></div></td><td class="code"><div class="code-highlight"><pre><span></span><span class="ch">#!/bin/bash</span>
        <span class="nb">echo</span> <span class="s2">&quot;hello&quot;</span>
        </pre></div>
        </td></tr></table>
        """
        source = safe_unicode(source)
        try:
            if flavored:
                source = cls._flavored_markdown(source)
            return markdown_mod.markdown(
                source,
                extensions=['markdown.extensions.codehilite', 'markdown.extensions.extra'],
                extension_configs={'markdown.extensions.codehilite': {'css_class': 'code-highlight'}})
        except Exception:
            log.error(traceback.format_exc())
            if safe:
                log.debug('Falling back to render in plain mode')
                return cls.plain(source)
            else:
                raise

    @classmethod
    def rst(cls, source, safe=True):
        source = safe_unicode(source)
        try:
            from docutils.core import publish_parts
            from docutils.parsers.rst import directives
            docutils_settings = dict([(alias, None) for alias in
                                cls.RESTRUCTUREDTEXT_DISALLOWED_DIRECTIVES])

            docutils_settings.update({'input_encoding': 'unicode',
                                      'report_level': 4})

            for k, v in docutils_settings.iteritems():
                directives.register_directive(k, v)

            parts = publish_parts(source=source,
                                  writer_name="html4css1",
                                  settings_overrides=docutils_settings)

            return parts['html_title'] + parts["fragment"]
        except ImportError:
            log.warning('Install docutils to use this function')
            return cls.plain(source)
        except Exception:
            log.error(traceback.format_exc())
            if safe:
                log.debug('Falling back to render in plain mode')
                return cls.plain(source)
            else:
                raise

    @classmethod
    def rst_with_mentions(cls, source):

        def wrapp(match_obj):
            uname = match_obj.groups()[0]
            return r'\ **@%(uname)s**\ ' % {'uname': uname}
        mention_hl = MENTIONS_REGEX.sub(wrapp, source).strip()
        return cls.rst(mention_hl)
