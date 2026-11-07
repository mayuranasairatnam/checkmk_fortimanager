"""
FortiManager datasource configuration.
"""
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice, CascadingSingleChoiceElement, Dictionary,
    DefaultValue, DictElement, Integer, Password, SingleChoice,
    SingleChoiceElement, String, migrate_to_password, validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic

# These extended forms support list defaults without changing saved rule values.
try:
    from cmk.rulesets.internal.form_specs import ListExtended
except ImportError:  # Checkmk 2.4
    from cmk.gui.form_specs.private.list_extended import ListExtended

try:
    from cmk.gui.form_specs.unstable.dictionary_extended import DictionaryExtended
except ImportError:  # Checkmk 2.4
    from cmk.gui.form_specs.private.dictionary_extended import DictionaryExtended


DEFAULT_EXCLUDED_ADOMS = (
    'FortiAnalyzer',
    'FortiAuthenticator',
    'FortiCache',
    'FortiCarrier',
    'FortiClient',
    'FortiDDoS',
    'FortiDeceptor',
    'FortiFirewall',
    'FortiFirewallCarrier',
    'FortiMail',
    'FortiManager',
    'FortiProxy',
    'FortiSandbox',
    'FortiWeb',
    'Syslog',
    'Unmanaged_Devices',
    'others',
    'rootp',
)


def _new_rule_defaults():
    """
    Activate new-rule exclusions when the constructor supports default_checked.

    Input:
        DictionaryExtended implementation provided by the installed Checkmk version.

    Output:
        Constructor options enabling prefilled exclusions in new rules without
        modifying existing saved exclusions or explicitly empty lists.

    """
    if 'default_checked' in DictionaryExtended.__dataclass_fields__:
        return {'default_checked': ['exclude_adoms']}
    return {}


def migrate_parameters(value):
    """
    Nest legacy credentials under authentication and remove obsolete overrides.

    Input:
        value: Raw value to validate or convert.

    Output:
        Migrated rule value; values outside the handled legacy format pass through.

    """
    if isinstance(value, dict):
        migrated = {key: entry for key, entry in value.items() if key not in ('address', 'ca_file')}
        if 'authentication' not in migrated and 'password' in migrated:
            method = migrated.pop('auth_method', 'password')
            password = migrated.pop('password')
            user = migrated.pop('user', '')
            migrated['authentication'] = (
                method, password if method == 'token' else {'user': user, 'password': password})
        return migrated
    return value


def parameter_form():
    """
    Build the Checkmk configuration form for special agent settings.

    Input:
        None.

    Output:
        Dictionary form specification with defaults and validation rules.

    """
    return DictionaryExtended(**_new_rule_defaults(), migrate=migrate_parameters, elements={
        'authentication': DictElement(required=True, parameter_form=CascadingSingleChoice(
            title=Title('Authentication method'),
            prefill=DefaultValue('password'),
            elements=[
                CascadingSingleChoiceElement(
                    name='password', title=Title('Admin user'),
                    parameter_form=Dictionary(elements={
                        'user': DictElement(required=True, parameter_form=String(
                            title=Title('API user name'),
                            custom_validate=(validators.LengthInRange(min_value=1),))),
                        'password': DictElement(required=True, parameter_form=Password(
                            title=Title('API password'), migrate=migrate_to_password)),
                    })),
                CascadingSingleChoiceElement(
                    name='token', title=Title('API user'),
                    parameter_form=Password(title=Title('API token'), migrate=migrate_to_password)),
            ],
            help_text=Help('Admin user uses a username and password. API user uses the generated token of a REST API Admin.'))),
        'port': DictElement(parameter_form=Integer(title=Title('HTTPS port'), prefill=DefaultValue(443),
            custom_validate=(validators.NetworkPort(),))),
        'timeout': DictElement(parameter_form=Integer(title=Title('Timeout per API request'),
            unit_symbol='seconds', prefill=DefaultValue(30),
            custom_validate=(validators.NumberInRange(min_value=1, max_value=300),))),
        'tls': DictElement(parameter_form=SingleChoice(title=Title('TLS certificate verification'),
            elements=[SingleChoiceElement(name='verify', title=Title('Verify certificate')),
                      SingleChoiceElement(name='skip', title=Title('Skip certificate verification'))],
            prefill=DefaultValue('verify'))),
        'exclude_adoms': DictElement(parameter_form=ListExtended(
            title=Title('ADOMs excluded from monitoring'),
            prefill=DefaultValue(list(DEFAULT_EXCLUDED_ADOMS)),
            element_template=String(custom_validate=(validators.LengthInRange(min_value=1),)),
            help_text=Help('Exact ADOM names. In Checkmk 2.5, new rules enable this option automatically. In Checkmk 2.4, enable it manually to use the suggested entries. Edit or clear the list to change the monitoring scope. Saved lists and empty or disabled exclusions remain unchanged. Excluded ADOMs are not queried or discovered.'))),
    })


rule_spec_fortimanager = SpecialAgent(
    name='fortimanager', title=Title('FortiManager'),
    topic=Topic.NETWORKING, parameter_form=parameter_form)
