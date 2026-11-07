"""
FortiManager: CPU, memory and disk resource checks.
"""

from cmk.agent_based.v2 import CheckPlugin, Metric, Result, State, check_levels, render

from ..lib.common import discover_resources, number, source


def check_resources(params, section):
    """
    Evaluate resources and report monitoring results.

    Input:
        params: Checkmk rule parameters, including the configured thresholds.
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Result objects and metrics produced by the check or its helpers.

    """
    data, error = source(section, 'resources')
    if error:
        yield Result(state=State.UNKNOWN, summary=error)
        return
    for field, label, metric, levels in (
        ('cpu_avg', 'CPU average', 'fmg_cpu_percent', 'cpu'),
        ('disk', 'Disk usage', 'fmg_disk_percent', 'disk'),
        ('memory', 'Memory usage', 'fmg_memory_percent', 'memory'),
    ):
        value = number(data.get(field))
        if value is None or not 0 <= value <= 100:
            yield Result(state=State.UNKNOWN, summary=f'{label}: missing or invalid percentage')
        else:
            yield from check_levels(value, levels_upper=params[levels], metric_name=metric,
                                    label=label, render_func=render.percent, boundaries=(0, 100))
    used, total = number(data.get('memory_used')), number(data.get('memory_total'))
    if used is None or total is None or total <= 0 or not 0 <= used <= total:
        yield Result(state=State.UNKNOWN, summary='Missing or invalid memory_used / memory_total')
        return
    factor = {'bytes': 1, 'kib': 1024, 'mib': 1024 ** 2}[params['memory_unit']]
    used, total = used * factor, total * factor
    yield Result(state=State.OK, summary=f'Memory: {render.bytes(used)} of {render.bytes(total)} used, {render.bytes(total - used)} free')
    for name, value in (('fmg_memory_used', used), ('fmg_memory_total', total), ('fmg_memory_free', total - used)):
        yield Metric(name, value, boundaries=(0, total))


check_plugin_fortimanager_resources = CheckPlugin(
    name='fortimanager_resources', sections=['fortimanager'], service_name='FortiManager Resources',
    discovery_function=discover_resources, check_function=check_resources,
    check_ruleset_name='fortimanager_resources', check_default_parameters={
        'cpu': ('fixed', (80.0, 90.0)), 'memory': ('fixed', (80.0, 90.0)),
        'disk': ('fixed', (80.0, 90.0)), 'memory_unit': 'kib'})
