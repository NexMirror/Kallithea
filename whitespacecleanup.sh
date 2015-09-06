#!/bin/bash -x

# Enforce some consistency in whitespace - just to avoid spurious whitespaces changes

files=`hg loc '*.py' '*.html' '*.css' '*.rst' '*.txt' '*.js' '*.ini' '*.cfg' CONTRIBUTORS LICENSE.md| egrep -v '/lockfiles.py|LICENSE-MERGELY.html|/codemirror/|/fontello/|(graph|mergely|native.history|select2/select2|yui.flot|yui.2.9)\.js$'`

sed -i -e "s,`printf '\t'`,    ,g" $files
sed -i -e "s,  *$,,g" $files
# ensure one trailing newline - remove empty last line and make last line include trailing newline:
sed -i -e '$,${/^$/d}' -e '$a\' $files

sed -i -e 's,\([^ /]\){,\1 {,g' `hg loc '*.css'`
sed -i -e 's|^\([^ /].*,\)\([^ ]\)|\1 \2|g' `hg loc '*.css'`

sed -i -e 's/^\(    [^: ]*\) *: *\([^/]\)/\1: \2/g' kallithea/public/css/{style,contextbar}.css
sed -i -e '1s|, |,|g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's/^\([^ ,/]\+ [^,]*[^ ,]\) *, *\(.\)/\1,\n\2/g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's/^\([^ ,/].*\)   */\1 /g' kallithea/public/css/{style,contextbar}.css
sed -i -e 's,^--$,-- ,g' kallithea/templates/email_templates/main.txt

hg mani | xargs chmod -x
hg loc 'set:!binary()&grep("^#!")&!(**_tmpl.py)&!(**/template**)' | xargs chmod +x

hg diff
