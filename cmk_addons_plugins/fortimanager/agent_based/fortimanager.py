"""
Compatibility imports for precompiled FortiManager checks created before the module split.

Implementations and plugin registrations live in the feature modules. Historical
attributes are resolved on demand so existing compiled imports keep working,
without exposing duplicate registrations during plugin discovery.
"""

from . import fortimanager_adoms as _adoms
from . import fortimanager_api as _api
from . import fortimanager_license as _license
from . import fortimanager_managed as _managed
from . import fortimanager_resources as _resources
from . import fortimanager_support as _support
from . import fortimanager_system as _system
from ..lib import common as _common


_EXPORTS = {
    'SYSTEM_FIELDS': _system.SYSTEM_FIELDS,
    'agent_section_fortimanager': _api.agent_section_fortimanager,
    'check_adoms': _adoms.check_adoms,
    'check_api': _api.check_api,
    'check_license': _license.check_license,
    'check_managed': _managed.check_managed,
    'check_plugin_fortimanager_adoms': _adoms.check_plugin_fortimanager_adoms,
    'check_plugin_fortimanager_api': _api.check_plugin_fortimanager_api,
    'check_plugin_fortimanager_license': _license.check_plugin_fortimanager_license,
    'check_plugin_fortimanager_managed': _managed.check_plugin_fortimanager_managed,
    'check_plugin_fortimanager_resources': _resources.check_plugin_fortimanager_resources,
    'check_plugin_fortimanager_support': _support.check_plugin_fortimanager_support,
    'check_plugin_fortimanager_system': _system.check_plugin_fortimanager_system,
    'check_resources': _resources.check_resources,
    'check_support': _support.check_support,
    'check_system': _system.check_system,
    'count': _common.count,
    'discover_adoms': _adoms.discover_adoms,
    'discover_single': _common.discover_single,
    'discover_license': _common.discover_license,
    'discover_resources': _common.discover_resources,
    'discover_system': _system.discover_system,
    'expiry_date': _support.expiry_date,
    'number': _common.number,
    'parse_fortimanager': _api.parse_fortimanager,
    'source': _common.source,
}


def __getattr__(name):
    """
    Resolve a historical function, constant or plugin registration by name.

    Input:
        name: Attribute imported by a previously compiled Checkmk check.

    Output:
        The original object from its feature module; raises AttributeError for
        names outside the compatibility exports.

    """
    try:
        return _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
