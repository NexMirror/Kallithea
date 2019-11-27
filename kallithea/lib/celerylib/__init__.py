# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
kallithea.lib.celerylib
~~~~~~~~~~~~~~~~~~~~~~~

celery libs for Kallithea

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 27, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging
import os
from hashlib import md5

from decorator import decorator
from tg import config

from kallithea import CELERY_EAGER, CELERY_ON
from kallithea.lib.pidlock import DaemonLock, LockHeld
from kallithea.lib.utils2 import safe_str
from kallithea.model import meta


log = logging.getLogger(__name__)


class FakeTask(object):
    """Fake a sync result to make it look like a finished task"""

    def __init__(self, result):
        self.result = result

    def failed(self):
        return False

    traceback = None # if failed

    task_id = None


def task(f_org):
    """Wrapper of celery.task.task, running async if CELERY_ON
    """

    if CELERY_ON:
        def f_async(*args, **kwargs):
            log.info('executing %s task', f_org.__name__)
            try:
                f_org(*args, **kwargs)
            finally:
                log.info('executed %s task', f_org.__name__)
        f_async.__name__ = f_org.__name__
        from kallithea.lib import celerypylons
        runner = celerypylons.task(ignore_result=True)(f_async)

        def f_wrapped(*args, **kwargs):
            t = runner.apply_async(args=args, kwargs=kwargs)
            log.info('executing task %s in async mode - id %s', f_org, t.task_id)
            return t
    else:
        def f_wrapped(*args, **kwargs):
            log.info('executing task %s in sync', f_org.__name__)
            try:
                result = f_org(*args, **kwargs)
            except Exception as e:
                log.error('exception executing sync task %s in sync: %r', f_org.__name__, e)
                raise # TODO: return this in FakeTask as with async tasks?
            return FakeTask(result)

    return f_wrapped


def __get_lockkey(func, *fargs, **fkwargs):
    params = list(fargs)
    params.extend(['%s-%s' % ar for ar in fkwargs.items()])

    func_name = str(func.__name__) if hasattr(func, '__name__') else str(func)

    lockkey = 'task_%s.lock' % \
        md5(func_name + '-' + '-'.join(map(safe_str, params))).hexdigest()
    return lockkey


def locked_task(func):
    def __wrapper(func, *fargs, **fkwargs):
        lockkey = __get_lockkey(func, *fargs, **fkwargs)
        lockkey_path = config.get('cache_dir') or config['app_conf']['cache_dir']  # Backward compatibility for TurboGears < 2.4

        log.info('running task with lockkey %s', lockkey)
        try:
            l = DaemonLock(os.path.join(lockkey_path, lockkey))
            ret = func(*fargs, **fkwargs)
            l.release()
            return ret
        except LockHeld:
            log.info('LockHeld')
            return 'Task with key %s already running' % lockkey

    return decorator(__wrapper, func)


def get_session():
    sa = meta.Session()
    return sa


def dbsession(func):
    def __wrapper(func, *fargs, **fkwargs):
        try:
            ret = func(*fargs, **fkwargs)
            return ret
        finally:
            if CELERY_ON and not CELERY_EAGER:
                meta.Session.remove()

    return decorator(__wrapper, func)
