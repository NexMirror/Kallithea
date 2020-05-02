# -*- coding: utf-8 -*-
"""
    vcs.backends.hg
    ~~~~~~~~~~~~~~~

    Mercurial backend implementation.

    :created_on: Apr 8, 2010
    :copyright: (c) 2010-2011 by Marcin Kuzminski, Lukasz Balcerzak.
"""

from kallithea.lib.vcs.utils import hgcompat

from .changeset import MercurialChangeset
from .inmemory import MercurialInMemoryChangeset
from .repository import MercurialRepository
from .workdir import MercurialWorkdir


__all__ = [
    'MercurialRepository', 'MercurialChangeset',
    'MercurialInMemoryChangeset', 'MercurialWorkdir',
]

hgcompat.monkey_do()
