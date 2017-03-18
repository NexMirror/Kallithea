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
    Pylons environment configuration
"""

import os
import kallithea
import pylons

from kallithea.config.app_cfg import setup_configuration

def load_environment(global_conf, app_conf,
                     test_env=None, test_index=None):
    """
    Configure the Pylons environment via the ``pylons.config``
    object
    """
    config = pylons.configuration.PylonsConfig()

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(
        root=root,
        controllers=os.path.join(root, 'controllers'),
        static_files=os.path.join(root, 'public'),
        templates=[os.path.join(root, 'templates')]
    )

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='kallithea', paths=paths)

    return setup_configuration(config, paths, app_conf, test_env, test_index)
