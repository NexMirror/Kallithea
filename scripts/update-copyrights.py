#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Kallithea script for maintaining contributor lists from version control
history.

This script and the data in it is a best effort attempt at reverse engineering
previous attributions and correlate that with version control history while
preserving all existing copyright statements and attribution. This script is
processing and summarizing information found elsewhere - it is not by itself
making any claims. Comments in the script are an attempt at reverse engineering
possible explanations - they are not showing any intent or confirming it is
correct.

Three files are generated / modified by this script:

kallithea/templates/about.html claims to show copyright holders, and the GPL
license requires such existing "legal notices" to be preserved. We also try to
keep it updated with copyright holders, but do not claim it is a correct list.

CONTRIBUTORS has the purpose of giving credit where credit is due and list all
the contributor names in the source.

kallithea/templates/base/base.html contains the copyright years in the page
footer.

Both make a best effort of listing all copyright holders, but revision control
history might be a better and more definitive source.

Contributors are sorted "fairly" by copyright year and amount of
contribution.

New contributors are listed, without considering if the contribution contains
copyrightable work.

When the copyright might belong to a different legal entity than the
contributor, the legal entity is given credit too.
"""


# Some committers are so wrong that it doesn't point at any contributor:
total_ignore = set()
total_ignore.add('*** failed to import extension hggit: No module named hggit')
total_ignore.add('<>')

# Normalize some committer names where people have contributed under different
# names or email addresses:
name_fixes = {}
name_fixes['Andrew Shadura'] = "Andrej Shadura <andrew@shadura.me>"
name_fixes['aparkar'] = "Aparkar <aparkar@icloud.com>"
name_fixes['Aras Pranckevicius'] = "Aras Pranckevičius <aras@unity3d.com>"
name_fixes['Augosto Hermann'] = "Augusto Herrmann <augusto.herrmann@planejamento.gov.br>"
name_fixes['"Bradley M. Kuhn" <bkuhn@ebb.org>'] = "Bradley M. Kuhn <bkuhn@sfconservancy.org>"
name_fixes['dmitri.kuznetsov'] = "Dmitri Kuznetsov"
name_fixes['Dmitri Kuznetsov'] = "Dmitri Kuznetsov"
name_fixes['domruf'] = "Dominik Ruf <dominikruf@gmail.com>"
name_fixes['Ingo von borstel'] = "Ingo von Borstel <kallithea@planetmaker.de>"
name_fixes['Jan Heylen'] = "Jan Heylen <heyleke@gmail.com>"
name_fixes['Jason F. Harris'] = "Jason Harris <jason@jasonfharris.com>"
name_fixes['Jelmer Vernooij'] = "Jelmer Vernooĳ <jelmer@samba.org>"
name_fixes['jfh <jason@jasonfharris.com>'] = "Jason Harris <jason@jasonfharris.com>"
name_fixes['Leonardo Carneiro<leonardo@unity3d.com>'] = "Leonardo Carneiro <leonardo@unity3d.com>"
name_fixes['leonardo'] = "Leonardo Carneiro <leonardo@unity3d.com>"
name_fixes['Leonardo <leo@unity3d.com>'] = "Leonardo Carneiro <leonardo@unity3d.com>"
name_fixes['Les Peabody'] = "Les Peabody <lpeabody@gmail.com>"
name_fixes['"Lorenzo M. Catucci" <lorenzo@sancho.ccd.uniroma2.it>'] = "Lorenzo M. Catucci <lorenzo@sancho.ccd.uniroma2.it>"
name_fixes['Lukasz Balcerzak'] = "Łukasz Balcerzak <lukaszbalcerzak@gmail.com>"
name_fixes['mao <mao@lins.fju.edu.tw>'] = "Ching-Chen Mao <mao@lins.fju.edu.tw>"
name_fixes['marcink'] = "Marcin Kuźmiński <marcin@python-works.com>"
name_fixes['Marcin Kuzminski'] = "Marcin Kuźmiński <marcin@python-works.com>"
name_fixes['nansenat16@null.tw'] = "nansenat16 <nansenat16@null.tw>"
name_fixes['Peter Vitt'] = "Peter Vitt <petervitt@web.de>"
name_fixes['philip.j@hostdime.com'] = "Philip Jameson <philip.j@hostdime.com>"
name_fixes['Søren Løvborg'] = "Søren Løvborg <sorenl@unity3d.com>"
name_fixes['Thomas De Schampheleire'] = "Thomas De Schampheleire <thomas.de_schampheleire@nokia.com>"
name_fixes['Weblate'] = "<>"
name_fixes['xpol'] = "xpol <xpolife@gmail.com>"
name_fixes['Lars <devel@sumpfralle.de>'] = "Lars Kruse <devel@sumpfralle.de>"


# Some committer email address domains that indicate that another entity might
# hold some copyright too:
domain_extra = {}
domain_extra['unity3d.com'] = "Unity Technologies"
domain_extra['rhodecode.com'] = "RhodeCode GmbH"

# Repository history show some old contributions that traditionally hasn't been
# listed in about.html - preserve that:
no_about = set(total_ignore)
# The following contributors were traditionally not listed in about.html and it
# seems unclear if the copyright is personal or belongs to a company.
no_about.add(('Thayne Harbaugh <thayne@fusionio.com>', '2011'))
no_about.add(('Dies Koper <diesk@fast.au.fujitsu.com>', '2012'))
no_about.add(('Erwin Kroon <e.kroon@smartmetersolutions.nl>', '2012'))
no_about.add(('Vincent Caron <vcaron@bearstech.com>', '2012'))
# These contributors' contributions might be too small to be copyrightable:
no_about.add(('philip.j@hostdime.com', '2012'))
no_about.add(('Stefan Engel <mail@engel-stefan.de>', '2012'))
no_about.add(('Ton Plomp <tcplomp@gmail.com>', '2013'))
# Was reworked and contributed later and shadowed by other contributions:
no_about.add(('Sean Farley <sean.michael.farley@gmail.com>', '2013'))

# Preserve contributors listed in about.html but not appearing in repository
# history:
other_about = [
    ("2011", "Aparkar <aparkar@icloud.com>"),
    ("2010", "RhodeCode GmbH"),
    ("2011", "RhodeCode GmbH"),
    ("2012", "RhodeCode GmbH"),
    ("2013", "RhodeCode GmbH"),
]

# Preserve contributors listed in CONTRIBUTORS but not appearing in repository
# history:
other_contributors = [
    ("", "Andrew Kesterson <andrew@aklabs.net>"),
    ("", "cejones"),
    ("", "David A. Sjøen <david.sjoen@westcon.no>"),
    ("", "James Rhodes <jrhodes@redpointsoftware.com.au>"),
    ("", "Jonas Oberschweiber <jonas.oberschweiber@d-velop.de>"),
    ("", "larikale"),
    ("", "RhodeCode GmbH"),
    ("", "Sebastian Kreutzberger <sebastian@rhodecode.com>"),
    ("", "Steve Romanow <slestak989@gmail.com>"),
    ("", "SteveCohen"),
    ("", "Thomas <thomas@rhodecode.com>"),
    ("", "Thomas Waldmann <tw-public@gmx.de>"),
]


import os
import re
from collections import defaultdict


def sortkey(x):
    """Return key for sorting contributors "fairly":
    * latest contribution
    * first contribution
    * number of contribution years
    * name (with some unicode normalization)
    The entries must be 2-tuples of a list of string years and the unicode name"""
    return (x[0] and -int(x[0][-1]),
            x[0] and int(x[0][0]),
            -len(x[0]),
            x[1].decode('utf-8').lower().replace(u'\xe9', u'e').replace(u'\u0142', u'l')
        )


def nice_years(l, dash='-', join=' '):
    """Convert a list of years into brief range like '1900-1901, 1921'."""
    if not l:
        return ''
    start = end = int(l[0])
    ranges = []
    for year in l[1:] + [0]:
        year = int(year)
        if year == end + 1:
            end = year
            continue
        if start == end:
            ranges.append('%s' % start)
        else:
            ranges.append('%s%s%s' % (start, dash, end))
        start = end = year
    assert start == 0 and end == 0, (start, end)
    return join.join(ranges)


def insert_entries(
        filename,
        all_entries,
        no_entries,
        domain_extra,
        split_re,
        normalize_name,
        format_f):
    """Update file with contributor information.
    all_entries: list of tuples with year and name
    no_entries: set of names or name and year tuples to ignore
    domain_extra: map domain name to extra credit name
    split_re: regexp matching the part of file to rewrite
    normalize_name: function to normalize names for grouping and display
    format_f: function formatting year list and name to a string
    """
    name_years = defaultdict(set)

    for year, name in all_entries:
        if name in no_entries or (name, year) in no_entries:
            continue
        domain = name.split('@', 1)[-1].rstrip('>')
        if domain in domain_extra:
            name_years[domain_extra[domain]].add(year)
        name_years[normalize_name(name)].add(year)

    l = [(list(sorted(year for year in years if year)), name)
         for name, years in name_years.items()]
    l.sort(key=sortkey)

    with open(filename) as f:
        pre, post = re.split(split_re, f.read())

    with open(filename, 'w') as f:
        f.write(pre +
                ''.join(format_f(years, name) for years, name in l) +
                post)


def main():
    repo_entries = [
        (year, name_fixes.get(name) or name_fixes.get(name.rsplit('<', 1)[0].strip()) or name)
        for year, name in
        (line.strip().split(' ', 1)
         for line in os.popen("""hg log -r '::.' -T '{date(date,"%Y")} {author}\n'""").readlines())
        ]

    insert_entries(
        filename='kallithea/templates/about.html',
        all_entries=repo_entries + other_about,
        no_entries=no_about,
        domain_extra=domain_extra,
        split_re=r'(?:  <li>Copyright &copy; [^\n]*</li>\n)*',
        normalize_name=lambda name: name.split('<', 1)[0].strip(),
        format_f=lambda years, name: '  <li>Copyright &copy; %s, %s</li>\n' % (nice_years(years, '&ndash;', ', '), name),
        )

    insert_entries(
        filename='CONTRIBUTORS',
        all_entries=repo_entries + other_contributors,
        no_entries=total_ignore,
        domain_extra=domain_extra,
        split_re=r'(?:    [^\n]*\n)*',
        normalize_name=lambda name: name,
        format_f=lambda years, name: ('    %s%s%s\n' % (name, ' ' if years else '', nice_years(years))),
        )

    insert_entries(
        filename='kallithea/templates/base/base.html',
        all_entries=repo_entries,
        no_entries=total_ignore,
        domain_extra={},
        split_re=r'(?<=&copy;) .* (?=by various authors)',
        normalize_name=lambda name: '',
        format_f=lambda years, name: ' ' + nice_years(years, '&ndash;', ', ') + ' ',
        )


if __name__ == '__main__':
    main()


# To list new contributors since last tagging:
# { hg log -r '::tagged()' -T '    {author}\n    {author}\n'; hg log -r '::.' -T '    {author}\n' | sort | uniq; } | sort | uniq -u
