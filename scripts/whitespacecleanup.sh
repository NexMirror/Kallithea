#!/bin/bash -x

# Enforce some consistency in whitespace - just to avoid spurious whitespaces changes

files=`hg mani | egrep -v '/codemirror/|/fontello/|/email_templates/|(/lockfiles.py|^LICENSE-MERGELY.html|^docs/Makefile|^scripts/whitespacecleanup.sh|/(graph|mergely|native.history|select2/select2|yui.flot|yui.2.9|jquery.dataTables)\.js|/test_dump_html_mails.ref.html|\.png|\.gif|\.ico|\.pot|\.po|\.mo|\.tar\.gz|\.diff)$'`

sed -i "s/`printf '\r'`//g" $files
sed -i -e "s,`printf '\t'`,    ,g" $files
sed -i -e "s,  *$,,g" $files
sed -i -e 's,\([^ ]\)\\$,\1 \\,g' -e 's,\(["'"'"']["'"'"']["'"'"']\) \\$,\1\\,g' $files
# ensure one trailing newline - remove empty last line and make last line include trailing newline:
sed -i -e '$,${/^$/d}' -e '$a\' $files

sed -i -e 's,\([^ /]\){,\1 {,g' `hg loc '*.css'`
sed -i -e 's|^\([^ /].*,\)\([^ ]\)|\1 \2|g' `hg loc '*.css'`

sed -i -e 's/^\(    [^: ]*\) *: *\([^/]\)/\1: \2/g' kallithea/public/css/{style,contextbar}.css
sed -i -e '1s|, |,|g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's/^\([^ ,/]\+ [^,]*[^ ,]\) *, *\(.\)/\1,\n\2/g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's/^\([^ ,/].*\)   */\1 /g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's,[ 	][ 	]*$,,g' -e 's, 	,	,g' kallithea/public/js/graph.js

hg mani | xargs chmod -x
hg loc 'set:!binary()&grep("^#!")&!(**_tmpl.py)&!(**/template**)' | xargs chmod +x

hg diff
