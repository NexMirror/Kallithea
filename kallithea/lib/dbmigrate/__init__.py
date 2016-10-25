from gearbox.command import Command

class UpgradeDb(Command):
    '''(removed)'''

    deprecated = True

    def run(self, args):
        raise SystemExit(
            'The "paster upgrade-db" command has been removed; please see the docs:\n'
            '    https://kallithea.readthedocs.io/en/default/upgrade.html'
        )
