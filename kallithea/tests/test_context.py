# Based on Turbogears2 2.3.8: util/webtest.py but almost entirely stripped
# and translator bits added.

import pylons
from pylons.i18n.translation import _get_translator

class test_context(object):
    def __init__(self, app):
        self._app = app

    def __enter__(self):
        # Initialize a translator for tests that utilize i18n
        translator = _get_translator(pylons.config.get('lang'))
        pylons.translator._push_object(translator)
        return self._app

    def __exit__(self, exc_type, exc_val, exc_tb):
        pylons.translator._pop_object()
