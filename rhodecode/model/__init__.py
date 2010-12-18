# -*- coding: utf-8 -*-
"""
    rhodecode.model.__init__
    ~~~~~~~~~~~~~~~~~~~~~~~~
    
    The application's model objects
    
    :created_on: Nov 25, 2010
    :author: marcink
    :copyright: (C) 2009-2010 Marcin Kuzminski <marcin@python-works.com>    
    :license: GPLv3, see COPYING for more details.
    
    
    :example:
    
        .. code-block:: python
    
           from paste.deploy import appconfig
           from pylons import config
           from sqlalchemy import engine_from_config
           from rhodecode.config.environment import load_environment
           
           conf = appconfig('config:development.ini', relative_to = './../../')
           load_environment(conf.global_conf, conf.local_conf)
           
           engine = engine_from_config(config, 'sqlalchemy.')
           init_model(engine)
           # RUN YOUR CODE HERE
    
"""
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License or (at your opinion) any later version of the license.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.

import logging
from rhodecode.model import meta
log = logging.getLogger(__name__)

def init_model(engine):
    """Initializes db session, bind the engine with the metadata,
    Call this before using any of the tables or classes in the model, preferably
    once in application start
    
    :param engine: engine to bind to
    """
    log.info("initializing db models for %s", engine)
    meta.Base.metadata.bind = engine

class BaseModel(object):
    """Base Model for all RhodeCode models, it adds sql alchemy session
    into instance of model
    
    :param sa: If passed it reuses this session instead of creating a new one
    """

    def __init__(self, sa=None):
        if sa is not None:
            self.sa = sa
        else:
            self.sa = meta.Session()
