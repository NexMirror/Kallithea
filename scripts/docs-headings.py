#!/usr/bin/env python2

"""
Consistent formatting of rst section titles
"""

from __future__ import print_function

import re
import subprocess


spaces = [
    (0, 1), # we assume this is a over-and-underlined header
    (2, 1),
    (1, 1),
    (1, 0),
    (1, 0),
    ]

# http://sphinx-doc.org/rest.html :
#   for the Python documentation, this convention is used which you may follow:
#   # with overline, for parts
#   * with overline, for chapters
#   =, for sections
#   -, for subsections
#   ^, for subsubsections
#   ", for paragraphs
pystyles = ['#', '*', '=', '-', '^', '"']

# match on a header line underlined with one of the valid characters
headermatch = re.compile(r'''\n*(.+)\n([][!"#$%&'()*+,./:;<=>?@\\^_`{|}~-])\2{2,}\n+''', flags=re.MULTILINE)


def main():
    filenames = subprocess.check_output(['hg', 'loc', 'set:**.rst+kallithea/i18n/how_to']).splitlines()
    for fn in filenames:
        print('processing %s' % fn)
        s = open(fn).read()

        # find levels and their styles
        lastpos = 0
        styles = []
        for markup in headermatch.findall(s):
            style = markup[1]
            if style in styles:
                stylepos = styles.index(style)
                if stylepos > lastpos + 1:
                    print('bad style %r with level %s - was at %s' % (style, stylepos, lastpos))
            else:
                stylepos = len(styles)
                if stylepos > lastpos + 1:
                    print('bad new style %r - expected %r' % (style, styles[lastpos + 1]))
                else:
                    styles.append(style)
            lastpos = stylepos

        # remove superfluous spacing (may however be restored by header spacing)
        s = re.sub(r'''(\n\n)\n*''', r'\1', s, flags=re.MULTILINE)

        if styles:
            newstyles = pystyles[pystyles.index(styles[0]):]

            def subf(m):
                title, style = m.groups()
                level = styles.index(style)
                before, after = spaces[level]
                newstyle = newstyles[level]
                return '\n' * (before + 1) + title + '\n' + newstyle * len(title) + '\n' * (after + 1)
            s = headermatch.sub(subf, s)

        # remove superfluous spacing when headers are adjacent
        s = re.sub(r'''(\n.+\n([][!"#$%&'()*+,./:;<=>?@\\^_`{|}~-])\2{2,}\n\n\n)\n*''', r'\1', s, flags=re.MULTILINE)
        # fix trailing space and spacing before link sections
        s = s.strip() + '\n'
        s = re.sub(r'''\n+((?:\.\. _[^\n]*\n)+)$''', r'\n\n\n\1', s)

        open(fn, 'w').write(s)

    print(subprocess.check_output(['hg', 'diff'] + filenames))

if __name__ == '__main__':
    main()
