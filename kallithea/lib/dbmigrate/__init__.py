from gearbox.command import Command


class UpgradeDb(Command):
    '''(removed)'''

    deprecated = True

    def run(self, args):
        raise SystemExit(
            'The "paster upgrade-db" command has been removed; please see the docs:\n'
            '    https://docs.kallithea-scm.org/en/default/upgrade.html'
        )
