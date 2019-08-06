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
kallithea.model.base
~~~~~~~~~~~~~~~~~~~~

The application's model objects

This file was forked by the Kallithea project in July 2014.
Original author and date, and relevant copyright and licensing information is below:
:created_on: Nov 25, 2010
:author: marcink
:copyright: (c) 2013 RhodeCode GmbH, and others.
:license: GPLv3, see LICENSE.md for more details.
"""


import logging

from kallithea.lib.utils2 import obfuscate_url_pw
from kallithea.model import meta


log = logging.getLogger(__name__)


def init_model(engine):
    """
    Initializes db session, bind the engine with the metadata,
    Call this before using any of the tables or classes in the model,
    preferably once in application start

    :param engine: engine to bind to
    """
    engine_str = obfuscate_url_pw(str(engine.url))
    log.info("initializing db for %s", engine_str)
    meta.Base.metadata.bind = engine
