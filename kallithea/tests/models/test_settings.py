from kallithea.model.db import Setting
from kallithea.model.meta import Session


name = 'spam-setting-name'


def test_passing_list_setting_value_results_in_string_valued_setting():
    assert Setting.get_by_name(name) is None
    setting = Setting.create_or_update(name, ['spam', 'eggs'])
    Session().flush() # must flush so we can delete it below
    try:
        assert Setting.get_by_name(name) is not None
        # Quirk: list value is stringified.
        assert Setting.get_by_name(name).app_settings_value \
               == "['spam', 'eggs']"
        assert Setting.get_by_name(name).app_settings_type == 'unicode'
    finally:
        Session().delete(setting)


def test_list_valued_setting_creation_requires_manual_value_formatting():
    assert Setting.get_by_name(name) is None
    # Quirk: need manual formatting of list setting value.
    setting = Setting.create_or_update(name, 'spam,eggs', type='list')
    Session().flush() # must flush so we can delete it below
    try:
        assert setting.app_settings_value == ['spam', 'eggs']
    finally:
        Session().delete(setting)


def test_list_valued_setting_update():
    assert Setting.get_by_name(name) is None
    setting = Setting.create_or_update(name, 'spam', type='list')
    Session().flush() # must flush so we can delete it below
    try:
        assert setting.app_settings_value == [u'spam']
        # Assign back setting value.
        setting.app_settings_value = setting.app_settings_value
        # Quirk: value is stringified on write and listified on read.
        assert setting.app_settings_value == ["[u'spam']"]
        setting.app_settings_value = setting.app_settings_value
        assert setting.app_settings_value == ["[u\"[u'spam']\"]"]
    finally:
        Session().delete(setting)
