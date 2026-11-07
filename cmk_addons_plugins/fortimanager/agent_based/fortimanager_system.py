"""
FortiManager: System identity and capacity checks.
"""

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, Service, State

from ..lib.common import count, source


SYSTEM_FIELDS = ('Hostname', 'Version', 'Serial Number', 'Platform Type', 'HA Mode',
                 'Max Number of Admin Domains', 'Max Number of Device Groups')


def discover_system(section):
    """
    Discover services for system.

    Input:
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Service objects according to the discovery conditions.

    """
    for field in SYSTEM_FIELDS:
        yield Service(item=field)


def check_system(item, section):
    """
    Evaluate system and report monitoring results.

    Input:
        item: Service item identifying the monitored entity.
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Result objects and metrics produced by the check or its helpers.

    """
    if item not in SYSTEM_FIELDS:
        yield Result(state=State.UNKNOWN, summary='System service replaced by dedicated sensors; run service discovery')
        return
    data, error = source(section, 'system')
    if error:
        yield Result(state=State.UNKNOWN, summary=error)
        return
    value = data.get(item)
    if value is None or value == '':
        yield Result(state=State.UNKNOWN, summary='Missing field: ' + item)
        return
    if item in ('Max Number of Admin Domains', 'Max Number of Device Groups'):
        capacity = count(value)
        if capacity is None:
            yield Result(state=State.UNKNOWN, summary='Invalid capacity: ' + str(value))
            return
        metric = 'fmg_max_adoms' if item == 'Max Number of Admin Domains' else 'fmg_max_device_groups'
        yield Metric(metric, capacity)
    yield Result(state=State.OK, summary=str(value))


check_plugin_fortimanager_system = CheckPlugin(
    name='fortimanager_system', sections=['fortimanager'], service_name='FortiManager System %s',
    discovery_function=discover_system, check_function=check_system)
