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

import os
import re
from collections import defaultdict

import contributor_data


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
        parts = name.split(' <', 1)
        if len(parts) == 2:
            name = parts[0] + ' <' + parts[1].lower()
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
        (year, contributor_data.name_fixes.get(name) or contributor_data.name_fixes.get(name.rsplit('<', 1)[0].strip()) or name)
        for year, name in
        (line.strip().split(' ', 1)
         for line in os.popen("""hg log -r '::.' -T '{date(date,"%Y")} {author}\n'""").readlines())
        ]

    insert_entries(
        filename='kallithea/templates/about.html',
        all_entries=repo_entries + contributor_data.other_about + contributor_data.other,
        no_entries=contributor_data.no_about,
        domain_extra=contributor_data.domain_extra,
        split_re=r'(?:  <li>Copyright &copy; [^\n]*</li>\n)*',
        normalize_name=lambda name: name.split('<', 1)[0].strip(),
        format_f=lambda years, name: '  <li>Copyright &copy; %s, %s</li>\n' % (nice_years(years, '&ndash;', ', '), name),
        )

    insert_entries(
        filename='CONTRIBUTORS',
        all_entries=repo_entries + contributor_data.other_contributors + contributor_data.other,
        no_entries=contributor_data.total_ignore,
        domain_extra=contributor_data.domain_extra,
        split_re=r'(?:    [^\n]*\n)*',
        normalize_name=lambda name: name,
        format_f=lambda years, name: ('    %s%s%s\n' % (name, ' ' if years else '', nice_years(years))),
        )

    insert_entries(
        filename='kallithea/templates/base/base.html',
        all_entries=repo_entries,
        no_entries=contributor_data.total_ignore,
        domain_extra={},
        split_re=r'(?<=&copy;) .* (?=by various authors)',
        normalize_name=lambda name: '',
        format_f=lambda years, name: ' ' + nice_years(years, '&ndash;', ', ') + ' ',
        )

    #docs/conf.py:copyright = u'2010-2016 by various authors, licensed as GPLv3.'
    insert_entries(
        filename='docs/conf.py',
        all_entries=repo_entries,
        no_entries=contributor_data.total_ignore,
        domain_extra={},
        split_re=r"(?<=copyright = u').*(?= by various authors)",
        normalize_name=lambda name: '',
        format_f=lambda years, name: nice_years(years, '-', ', '),
        )


if __name__ == '__main__':
    main()


# To list new contributors since last tagging:
# { hg log -r '::tagged()' -T '    {author}\n    {author}\n'; hg log -r '::.' -T '    {author}\n' | sort | uniq; } | sort | uniq -u
