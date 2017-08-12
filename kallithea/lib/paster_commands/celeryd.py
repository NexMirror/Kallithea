# -*- coding: utf-8 -*-

import argparse

import kallithea
from kallithea.lib.paster_commands.common import BasePasterCommand
from kallithea.lib.utils2 import str2bool

__all__ = ['Command']


class Command(BasePasterCommand):
    """Kallithea: Celery worker for asynchronous tasks"""

    # Starts the celery worker using configuration from a paste.deploy
    # configuration file.

    def take_action(self, args):
        if not kallithea.CELERY_ON:
            raise Exception('Please set use_celery = true in .ini config '
                            'file before running celeryd')

        from kallithea.lib import celerypylons
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
