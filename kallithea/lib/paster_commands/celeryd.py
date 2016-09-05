# -*- coding: utf-8 -*-

import kallithea
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils import load_rcextensions
from kallithea.lib.utils2 import str2bool

__all__ = ['Command']


class Command(BasePasterCommand):
    """Start the celery worker

    Starts the celery worker that uses a paste.deploy configuration
    file.
    """

    usage = 'CONFIG_FILE [celeryd options...]'
    summary = __doc__.splitlines()[0]
    description = "".join(__doc__.splitlines()[2:])
    group_name = "Kallithea"

    parser = BasePasterCommand.standard_parser(quiet=True)

    def update_parser(self):
        from kallithea.lib import celerypylons
        cmd = celerypylons.worker.worker(celerypylons.app.app_or_default())
        for x in cmd.get_options():
            self.parser.add_option(x)

    def command(self):
        from kallithea.lib import celerypylons
        from pylons import config
        try:
            CELERY_ON = str2bool(config['app_conf'].get('use_celery'))
        except KeyError:
            CELERY_ON = False

        if not CELERY_ON:
            raise Exception('Please set use_celery = true in .ini config '
                            'file before running celeryd')
        kallithea.CELERY_ON = CELERY_ON

        load_rcextensions(config['here'])
        cmd = celerypylons.worker.worker(celerypylons.app.app_or_default())
        return cmd.run(**vars(self.options))
