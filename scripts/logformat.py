#!/usr/bin/env python2

import re
import sys

if len(sys.argv) < 2:
    print 'Cleanup of superfluous % formatting of log statements.'
    print 'Usage:'
    print '''  hg revert `hg loc '*.py'|grep -v logformat.py` && scripts/logformat.py `hg loc '*.py'` && hg diff'''
    raise SystemExit(1)


logre = r'''
(log\.(?:error|info|warning|debug)
[(][ \n]*
)
%s
(
[ \n]*[)]
)
'''
res = [
    # handle % () - keeping spaces around the old %
    (re.compile(logre % r'''("[^"]*"|'[^']*')   ([\n ]*) %  ([\n ]*) \( ( (?:[^()]|\n)* (?: \( (?:[^()]|\n)* \) (?:[^()]|\n)* )* ) \) ''', flags=re.MULTILINE|re.VERBOSE), r'\1\2,\3\4\5\6'),
    # handle % without () - keeping spaces around the old %
    (re.compile(logre % r'''("[^"]*"|'[^']*')   ([\n ]*) %  ([\n ]*)    ( (?:[^()]|\n)* (?: \( (?:[^()]|\n)* \) (?:[^()]|\n)* )* )    ''', flags=re.MULTILINE|re.VERBOSE), r'\1\2,\3\4\5\6'),
    # remove extra space if it is on next line
    (re.compile(logre % r'''("[^"]*"|'[^']*') , (\n [ ]) ([ ][\n ]*)    ( (?:[^()]|\n)* (?: \( (?:[^()]|\n)* \) (?:[^()]|\n)* )* )    ''', flags=re.MULTILINE|re.VERBOSE), r'\1\2,\3\4\5\6'),
    # remove extra space if it is on same line
    (re.compile(logre % r'''("[^"]*"|'[^']*') , [ ]+  () (   [\n ]+)    ( (?:[^()]|\n)* (?: \( (?:[^()]|\n)* \) (?:[^()]|\n)* )* )    ''', flags=re.MULTILINE|re.VERBOSE), r'\1\2,\3\4\5\6'),
    # remove trailing , and space
    (re.compile(logre % r'''("[^"]*"|'[^']*') ,       () (   [\n ]*)    ( (?:[^()]|\n)* (?: \( (?:[^()]|\n)* \) (?:[^()]|\n)* )* [^(), \n] ) [ ,]*''', flags=re.MULTILINE|re.VERBOSE), r'\1\2,\3\4\5\6'),
    ]

for f in sys.argv[1:]:
    s = open(f).read()
    for r, t in res:
        s = r.sub(t, s)
    open(f, 'w').write(s)
