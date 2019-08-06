#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Kallithea script for generating a quick overview of contributors and their
commit counts in a given revision set.
"""
import argparse
import os
from collections import Counter

import contributor_data


def main():

    parser = argparse.ArgumentParser(description='Generate a list of committers and commit counts.')
    parser.add_argument('revset',
                        help='revision set specifying the commits to count')
    args = parser.parse_args()

    repo_entries = [
        (contributor_data.name_fixes.get(name) or contributor_data.name_fixes.get(name.rsplit('<', 1)[0].strip()) or name).rsplit('<', 1)[0].strip()
        for name in (line.strip()
         for line in os.popen("""hg log -r '%s' -T '{author}\n'""" % args.revset).readlines())
        ]

    counter = Counter(repo_entries)
    for name, count in counter.most_common():
        if name == '':
            continue
        print('%4s %s' % (count, name))


if __name__ == '__main__':
    main()
