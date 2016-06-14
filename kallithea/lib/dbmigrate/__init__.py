from paste.script.command import Command

class UpgradeDb(Command):
    hidden = True
    summary = '(removed)'

    def run(self, args):
        raise SystemExit('The "paster upgrade-db" command has been removed.')
