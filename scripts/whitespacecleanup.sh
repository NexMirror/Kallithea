#!/bin/bash -x

# Enforce some consistency in whitespace - just to avoid spurious whitespaces changes

files=`hg mani | egrep -v '/fontello/|/email_templates/|(^LICENSE-MERGELY.html|^docs/Makefile|^scripts/whitespacecleanup.sh|/(graph|mergely|native.history)\.js|/test_dump_html_mails.ref.html|\.png|\.gif|\.ico|\.pot|\.po|\.mo|\.tar\.gz|\.diff)$'`

sed -i "s/`printf '\r'`//g" $files
sed -i -e "s,`printf '\t'`,    ,g" $files
sed -i -e "s,  *$,,g" $files
sed -i -e 's,\([^ ]\)\\$,\1 \\,g' -e 's,\(["'"'"']["'"'"']["'"'"']\) \\$,\1\\,g' $files
# ensure one trailing newline - remove empty last line and make last line include trailing newline:
sed -i -e '$,${/^$/d}' -e '$a\' $files

sed -i -e 's,\([^ /]\){,\1 {,g' `hg loc '*.css'`
sed -i -e 's|^\([^ /].*,\)\([^ ]\)|\1 \2|g' `hg loc '*.css'`

hg mani | xargs chmod -x
hg loc 'set:!binary()&grep("^#!")&!(**_tmpl.py)&!(**/template**)' | xargs chmod +x

# isort is installed from dev_requirements.txt
isort --line-width 160 --wrap-length 160 --lines-after-imports 2 `hg loc '*.py'`

hg diff
