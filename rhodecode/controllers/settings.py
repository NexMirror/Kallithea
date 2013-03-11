# -*- coding: utf-8 -*-
"""
    rhodecode.controllers.settings
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Settings controller for rhodecode

    :created_on: Jun 30, 2010
    :author: marcink
    :copyright: (C) 2010-2012 Marcin Kuzminski <marcin@python-works.com>
    :license: GPLv3, see COPYING for more details.
"""
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

import logging
import traceback
import formencode

from formencode import htmlfill

from pylons import tmpl_context as c, request, url
from pylons.controllers.util import redirect
from pylons.i18n.translation import _

import rhodecode.lib.helpers as h

from rhodecode.lib.auth import LoginRequired, HasRepoPermissionAllDecorator,\
    HasRepoPermissionAnyDecorator
from rhodecode.lib.base import BaseRepoController, render
from rhodecode.lib.utils import invalidate_cache, action_logger

from rhodecode.model.forms import RepoSettingsForm
from rhodecode.model.repo import RepoModel
from rhodecode.model.db import RepoGroup, Repository
from rhodecode.model.meta import Session
from rhodecode.model.scm import ScmModel

log = logging.getLogger(__name__)


class SettingsController(BaseRepoController):

    @LoginRequired()
    def __before__(self):
        super(SettingsController, self).__before__()

    def __load_defaults(self):
        c.repo_groups = RepoGroup.groups_choices(check_perms=True)
        c.repo_groups_choices = map(lambda k: unicode(k[0]), c.repo_groups)

        repo_model = RepoModel()
        c.users_array = repo_model.get_users_js()
        c.users_groups_array = repo_model.get_users_groups_js()
        choices, c.landing_revs = ScmModel().get_repo_landing_revs()
        c.landing_revs_choices = choices

    def __load_data(self, repo_name=None):
        """
        Load defaults settings for edit, and update

        :param repo_name:
        """
        self.__load_defaults()

        c.repo_info = db_repo = Repository.get_by_repo_name(repo_name)
        repo = db_repo.scm_instance

        if c.repo_info is None:
            h.not_mapped_error(repo_name)
            return redirect(url('home'))

        ##override defaults for exact repo info here git/hg etc
        choices, c.landing_revs = ScmModel().get_repo_landing_revs(c.repo_info)
        c.landing_revs_choices = choices

        defaults = RepoModel()._get_defaults(repo_name)

        return defaults

    @HasRepoPermissionAllDecorator('repository.admin')
    def index(self, repo_name):
        defaults = self.__load_data(repo_name)

        return htmlfill.render(
            render('settings/repo_settings.html'),
            defaults=defaults,
            encoding="UTF-8",
            force_defaults=False
        )

    @HasRepoPermissionAllDecorator('repository.admin')
    def update(self, repo_name):
        self.__load_defaults()
        repo_model = RepoModel()
        changed_name = repo_name
        #override the choices with extracted revisions !
        choices, c.landing_revs = ScmModel().get_repo_landing_revs(repo_name)
        c.landing_revs_choices = choices
        repo = Repository.get_by_repo_name(repo_name)
        _form = RepoSettingsForm(edit=True,
                                old_data={'repo_name': repo_name,
                                          'repo_group': repo.group.get_dict() \
                                              if repo.group else {}},
                                 repo_groups=c.repo_groups_choices,
                                 landing_revs=c.landing_revs_choices)()
        try:
            form_result = _form.to_python(dict(request.POST))
            repo_model.update(repo_name, **form_result)
            invalidate_cache('get_repo_cached_%s' % repo_name)
            h.flash(_('Repository %s updated successfully') % repo_name,
                    category='success')
            changed_name = form_result['repo_name_full']
            action_logger(self.rhodecode_user, 'user_updated_repo',
                          changed_name, self.ip_addr, self.sa)
            Session().commit()
        except formencode.Invalid, errors:
            defaults = self.__load_data(repo_name)
            defaults.update(errors.value)
            return htmlfill.render(
                render('settings/repo_settings.html'),
                defaults=errors.value,
                errors=errors.error_dict or {},
                prefix_error=False,
                encoding="UTF-8")

        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('error occurred during update of repository %s') \
                    % repo_name, category='error')

        return redirect(url('repo_settings_home', repo_name=changed_name))

    @HasRepoPermissionAllDecorator('repository.admin')
    def delete(self, repo_name):
        """DELETE /repos/repo_name: Delete an existing item"""
        # Forms posted to this method should contain a hidden field:
        #    <input type="hidden" name="_method" value="DELETE" />
        # Or using helpers:
        #    h.form(url('repo_settings_delete', repo_name=ID),
        #           method='delete')
        # url('repo_settings_delete', repo_name=ID)

        repo_model = RepoModel()
        repo = repo_model.get_by_repo_name(repo_name)
        if not repo:
            h.not_mapped_error(repo_name)
            return redirect(url('home'))
        try:
            action_logger(self.rhodecode_user, 'user_deleted_repo',
                              repo_name, self.ip_addr, self.sa)
            repo_model.delete(repo)
            invalidate_cache('get_repo_cached_%s' % repo_name)
            h.flash(_('deleted repository %s') % repo_name, category='success')
            Session().commit()
        except Exception:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during deletion of %s') % repo_name,
                    category='error')

        return redirect(url('admin_settings_my_account', anchor='my'))

    @HasRepoPermissionAnyDecorator('repository.write', 'repository.admin')
    def toggle_locking(self, repo_name):
        """
        Toggle locking of repository by simple GET call to url

        :param repo_name:
        """

        try:
            repo = Repository.get_by_repo_name(repo_name)

            if repo.enable_locking:
                if repo.locked[0]:
                    Repository.unlock(repo)
                    action = _('unlocked')
                else:
                    Repository.lock(repo, c.rhodecode_user.user_id)
                    action = _('locked')

                h.flash(_('Repository has been %s') % action,
                        category='success')
        except Exception, e:
            log.error(traceback.format_exc())
            h.flash(_('An error occurred during unlocking'),
                    category='error')
        return redirect(url('summary_home', repo_name=repo_name))
