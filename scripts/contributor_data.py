# -*- coding: utf-8 -*-

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
name_fixes['mikespook'] = "mikespook <mikespook@gmail.com>"
name_fixes['nansenat16@null.tw'] = "nansenat16 <nansenat16@null.tw>"
name_fixes['Peter Vitt'] = "Peter Vitt <petervitt@web.de>"
name_fixes['philip.j@hostdime.com'] = "Philip Jameson <philip.j@hostdime.com>"
name_fixes['Søren Løvborg'] = "Søren Løvborg <sorenl@unity3d.com>"
name_fixes['Thomas De Schampheleire'] = "Thomas De Schampheleire <thomas.de_schampheleire@nokia.com>"
name_fixes['Hosted Weblate'] = "<>"
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

# Contributors in about.html and CONTRIBUTORS not appearing in repository
# history:
other = [
    # Work folded into commits attributed to others:
    ('2013', 'Ilya Beda <ir4y.ix@gmail.com>'),
    ('2015', 'Bradley M. Kuhn <bkuhn@sfconservancy.org>'),
    # Translators previously listed in
    # kallithea/i18n/*/LC_MESSAGES/kallithea.po and originating from before the
    # use of Weblate.
    ('2012', 'Augusto Herrmann <augusto.herrmann@gmail.com>'),
    ('2012', 'Nemcio <areczek01@gmail.com>'),
    ('2012', 'Nemcio <bogdan114@g.pl>'),
    ('2013', 'Andrey Mivrenik <myvrenik@gmail.com>'),
    ('2013', 'ArcheR <aleclitvinov1980@gmail.com>'),
    ('2013', 'gnustavo <gustavo@gnustavo.com>'),
    ('2013', 'ivlevdenis <ivlevdenis.ru@gmail.com>'),
    ('2013', 'Mikhail Zholobov <legal90@gmail.com>'),
    ('2013', 'mokeev1995 <mokeev_andre@mail.ru>'),
    ('2013', 'Nemcio <areczek01@gmail.com>'),
    ('2013', 'Ruslan Bekenev <furyinbox@gmail.com>'),
    ('2013', 'shirou - しろう'),
    ('2013', 'softforwinxp <softforwinxp@gmail.com>'),
    ('2013', 'stephanj <info@stephan-jauernick.de>'),
    ('2013', 'zhmylove <zhmylove@narod.ru>'),
    ('2013', 'こいんとす <tkondou@gmail.com>'),
    ('2014', 'invision70 <invision70@gmail.com>'),
    ('2014', 'SkryabinD <skryabind@gmail.com>'),
    ('2014', 'whosaysni <whosaysni@gmail.com>'),
]

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
