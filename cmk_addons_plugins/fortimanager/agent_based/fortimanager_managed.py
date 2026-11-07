"""
FortiManager: Managed device count checks.
"""

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, State

from ..lib.common import count, discover_license, source


def check_managed(section):
    """
    Evaluate managed and report monitoring results.

    Input:
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Result objects and metrics produced by the check or its helpers.

    """
    data, error = source(section, 'license')
    if error:
        yield Result(state=State.UNKNOWN, summary=error)
        return
    raw = data.get('dev_num_count')
    raw = raw if isinstance(raw, dict) else {}
    for key, name, label in (('fgt_cnt', 'fmg_fortigates', 'FortiGates'),
                             ('fap_cnt', 'fmg_fortiap', 'FortiAPs'),
                             ('fsw_cnt', 'fmg_fortiswitch', 'FortiSwitches'),
                             ('fex_cnt', 'fmg_fortiextender', 'FortiExtenders')):
        entry = raw.get(key)
        if key == 'fex_cnt' and key not in raw:
            yield Result(state=State.OK, summary='FortiExtenders: not reported by API')
            continue
        value = count(entry.get('val')) if isinstance(entry, dict) else None
        if value is None:
            yield Result(state=State.UNKNOWN, summary=f'{label}: missing or invalid count')
        else:
            yield Result(state=State.OK, summary=f'{label}: {value:.0f}')
            yield Metric(name, value)


check_plugin_fortimanager_managed = CheckPlugin(
    name='fortimanager_managed', sections=['fortimanager'], service_name='FortiManager Managed Devices',
    discovery_function=discover_license, check_function=check_managed)
