# -*- coding: utf-8 -*-

import argparse

import kallithea
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils import load_rcextensions
from kallithea.lib.utils2 import str2bool

__all__ = ['Command']


class Command(BasePasterCommand):
    """Kallithea: Celery worker for asynchronous tasks"""

    # Starts the celery worker using configuration from a paste.deploy
    # configuration file.

    requires_db_session = False # will start session on demand

    def take_action(self, args):
        from kallithea.lib import celerypylons
        from tg import config
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

        celery_args = args.celery_args
        if '--' in celery_args:
            celery_args.remove('--')

        return cmd.run_from_argv('kallithea celery worker', celery_args)

    def get_parser(self, prog_name):
        parser = super(Command, self).get_parser(prog_name)

        parser.add_argument('celery_args', nargs=argparse.REMAINDER,
            help="Pass extra options to Celery after a '--' separator",
            )

        return parser
