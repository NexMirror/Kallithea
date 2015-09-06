#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from sqlalchemy.util import OrderedDict


__all__ = ['databases', 'operations']

databases = ('sqlite', 'postgres', 'mysql', 'oracle', 'mssql', 'firebird')

# Map operation names to function names
operations = OrderedDict()
operations['upgrade'] = 'upgrade'
operations['downgrade'] = 'downgrade'
