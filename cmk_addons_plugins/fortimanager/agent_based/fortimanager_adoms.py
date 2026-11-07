"""
FortiManager: ADOM discovery and monitoring checks.
"""

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, Service, State

from ..lib.common import count, source


def discover_adoms(section):
    """
    Discover services for ADOMs.

    Input:
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Service objects according to the discovery conditions.

    """
    data, error = source(section, 'adoms')
    if not error:
        for name in sorted(data):
            yield Service(item=name)


def check_adoms(item, section):
    """
    Evaluate ADOMs and report monitoring results.

    Input:
        item: Service item identifying the monitored entity.
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Result objects and metrics produced by the check or its helpers.

    """
    data, error = source(section, 'adoms')
    if error:
        yield Result(state=State.UNKNOWN, summary=error)
        return
    entry = data.get(item)
    if not isinstance(entry, dict):
        yield Result(state=State.UNKNOWN, summary='ADOM no longer returned by API; run service discovery')
        return
    if entry.get('error'):
        yield Result(state=State.UNKNOWN, summary=str(entry['error']))
        return
    value = count(entry.get('count'))
    if value is None:
        yield Result(state=State.UNKNOWN, summary='Missing or invalid ADOM device count')
    else:
        yield Result(state=State.OK, summary=f'Devices: {value:.0f}')
        yield Metric('devices', value)


check_plugin_fortimanager_adoms = CheckPlugin(
    name='fortimanager_adoms', sections=['fortimanager'], service_name='FortiManager ADOM %s Devices',
    discovery_function=discover_adoms, check_function=check_adoms)
