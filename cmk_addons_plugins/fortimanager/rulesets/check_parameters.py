"""
Threshold rules for FortiManager checks.
"""
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue, DictElement, Dictionary, Integer, LevelDirection, List, Percentage,
    SimpleLevels, SingleChoice, SingleChoiceElement, String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def utilization(title):
    """
    Build the Checkmk configuration form for utilization.

    Input:
        title: Title displayed in the configuration form.

    Output:
        Required DictElement containing percentage warning and critical levels.

    """
    return DictElement(required=True, parameter_form=SimpleLevels[float](
        title=Title(title), form_spec_template=Percentage(), level_direction=LevelDirection.UPPER,
        prefill_fixed_levels=DefaultValue((80.0, 90.0))))


def license_form():
    """
    Build the Checkmk configuration form for license.

    Input:
        None.

    Output:
        Dictionary form specification with defaults and validation rules.

    """
    return Dictionary(elements={'levels': utilization('Device license utilization')})


def resource_form():
    """
    Build the Checkmk configuration form for resource.

    Input:
        None.

    Output:
        Dictionary form specification with defaults and validation rules.

    """
    return Dictionary(elements={
        'cpu': utilization('CPU average'), 'memory': utilization('Memory utilization'),
        'disk': utilization('Disk utilization'),
        'memory_unit': DictElement(required=True, parameter_form=SingleChoice(
            title=Title('Unit of memory_used and memory_total in API response'),
            help_text=Help('Verify this unit against your FortiManager firmware. Percentages are not converted.'),
            elements=[SingleChoiceElement(name='bytes', title=Title('Bytes')),
                      SingleChoiceElement(name='kib', title=Title('KiB')),
                      SingleChoiceElement(name='mib', title=Title('MiB'))], prefill=DefaultValue('kib'))),
    })


def support_form():
    """
    Build the Checkmk configuration form for support.

    Input:
        None.

    Output:
        Dictionary form specification with defaults and validation rules.

    """
    return Dictionary(elements={
        'expiry': DictElement(required=True, parameter_form=SimpleLevels[int](
            title=Title('Remaining support lifetime'), form_spec_template=Integer(unit_symbol='days'),
            level_direction=LevelDirection.LOWER, prefill_fixed_levels=DefaultValue((30, 14)))),
        'valid_statuses': DictElement(parameter_form=List(
            title=Title('API status values indicating valid support'), element_template=String(),
            help_text=Help('Default valid values: valid, active, licensed, ok. Configuring this list replaces these defaults. Unknown and undocumented numeric statuses remain UNKNOWN. Add the numeric value as a string only after verifying its meaning for your firmware.'))),
    })


rule_spec_fortimanager_license = CheckParameters(
    name='fortimanager_license', title=Title('FortiManager device license utilization'),
    topic=Topic.APPLICATIONS, parameter_form=license_form, condition=HostCondition())
rule_spec_fortimanager_resources = CheckParameters(
    name='fortimanager_resources', title=Title('FortiManager resources'),
    topic=Topic.APPLICATIONS, parameter_form=resource_form, condition=HostCondition())
rule_spec_fortimanager_support = CheckParameters(
    name='fortimanager_support', title=Title('FortiManager support expiration'),
    topic=Topic.APPLICATIONS, parameter_form=support_form, condition=HostCondition())
