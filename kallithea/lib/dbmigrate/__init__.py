from paste.script.command import Command

class UpgradeDb(Command):
    hidden = True
    summary = '(removed)'

    def run(self, args):
        raise SystemExit(
            'The "paster upgrade-db" command has been removed; please see the docs:\n'
            '    https://kallithea.readthedocs.io/en/default/upgrade.html'
        )
