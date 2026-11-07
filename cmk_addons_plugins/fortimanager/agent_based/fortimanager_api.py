"""
FortiManager: JSON section parser and API collection status check.
"""

import json

from cmk.agent_based.v2 import AgentSection, CheckPlugin, Result, State

from ..lib.common import discover_single


def parse_fortimanager(string_table):
    """
    Parse the JSON agent payload for FortiManager.

    Input:
        string_table: Checkmk section rows containing the JSON agent payload.

    Output:
        Parsed section data, or an API error section when the JSON payload is invalid.

    """
    try:
        data = json.loads(''.join(row[0] for row in string_table if row))
        if isinstance(data, dict):
            return data
    except (ValueError, TypeError):
        pass
    return {'api': {'errors': ['Invalid FortiManager agent data']}}


agent_section_fortimanager = AgentSection(name='fortimanager', parse_function=parse_fortimanager)


def check_api(section):
    """
    Evaluate API and report monitoring results.

    Input:
        section: Parsed agent data for the registered section.

    Output:
        Yields Checkmk Result objects with monitoring states and diagnostic details.

    """
    api = section.get('api')
    if not isinstance(api, dict) or not isinstance(api.get('errors'), list):
        yield Result(state=State.UNKNOWN, summary='Missing API collection status')
    elif api['errors']:
        yield Result(state=State.CRIT, summary='; '.join(str(e) for e in api['errors']))
    elif api.get('authentication') == 'token':
        yield Result(state=State.OK, summary='All API queries successful; API token, GUI queries disabled')
    else:
        yield Result(state=State.OK, summary='All API queries successful; session closed')


check_plugin_fortimanager_api = CheckPlugin(
    name='fortimanager_api', sections=['fortimanager'], service_name='FortiManager API',
    discovery_function=discover_single, check_function=check_api)
