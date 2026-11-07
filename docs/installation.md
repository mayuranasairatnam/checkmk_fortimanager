# Installation and configuration

[← README](../README.md) · [Installation](installation.md) · [Authentication](authentication.md) · [Monitoring](monitoring.md) · [Development](development.md)

## Requirements

- Checkmk **2.4 or 2.5**, with Python **3.11+** and `requests` in the site environment.
- HTTPS access from the Checkmk site to the FortiManager appliance.
- A dedicated account or API token with the [required permissions](authentication.md).

## Install the package

Download the MKP using **Download MKP** in the [README](../README.md), then upload
and enable it under **Setup → Maintenance → Extension packages**. The package ID
is `check_fortimanager`. No Checkmk agent is required on the monitored system.

Alternatively, as the Checkmk site user, replace `VERSION` with the downloaded
package version:

```sh
mkp add /path/to/check_fortimanager-VERSION.mkp
mkp enable check_fortimanager VERSION
```

To build locally, run `python3 -B build_mkp.py` from the repository directory.
See [development](development.md) for local setup and checks.

## Configure the host and rule

1. Create a FortiManager host with the appliance's DNS name or IP address.
   Select **Configured API integrations, no Checkmk agent** as the data source.
2. In **Setup**, search for **FortiManager** and open the integration ruleset.
   Create a new rule and restrict its **Conditions → Explicit hosts** to the
   host created above.
3. Select **Authentication method** and enter the matching credentials:

   | Authentication method | Required fields |
   | --- | --- |
   | **Admin user** (default) | **API user name** and **API password** |
   | **API user** | **API token** |

   Use the Checkmk Password Store for passwords and tokens.
4. Review **ADOMs excluded from monitoring**. Checkmk 2.5 enables the
   prefilled list for new rules; in Checkmk 2.4, enable it manually if needed.
   See [Default ADOM exclusions](#default-adom-exclusions).
5. Review the [connection settings](#connection-settings), then save the rule.
6. Activate changes and continue with [service discovery](#discover-and-check-services).

## Connection settings

| Setting | Default / behavior |
| --- | --- |
| Target address | Checkmk host primary address; falls back to the host name |
| HTTPS port | 443; configurable from 1 to 65535 |
| Timeout per API request | 30 seconds; rule accepts 1 to 300 seconds |
| TLS certificate verification | Enabled; uses the Python environment's default trust store |

The certificate must match the target address. There is no separate API address
or CA bundle override. See [authentication](authentication.md) for permissions.

## Discover and check services

Run service discovery on the host, accept the discovered services and activate
changes. Inspect **FortiManager API** for collection errors. After changing the
monitoring scope, rescan the host and use **Remove vanished services** for items
that are no longer monitored.

New ADOMs appear during normal service discovery. Configure periodic service
discovery if new services should be accepted automatically. Removed ADOMs can
remain UNKNOWN until their vanished services are removed. A failed ADOM list
query does not remove stored services.

As the Checkmk site user, run discovery and check the result:

```sh
cmk -vI YOUR_HOST
cmk -nv YOUR_HOST
```

## Default ADOM exclusions

In Checkmk 2.5, new rules enable the optional exclusion list automatically.
In Checkmk 2.4, enable the option manually to apply the exclusions.
In both versions, the list is prefilled with these exact names:

```text
FortiAnalyzer
FortiAuthenticator
FortiCache
FortiCarrier
FortiClient
FortiDDoS
FortiDeceptor
FortiFirewall
FortiFirewallCarrier
FortiMail
FortiManager
FortiProxy
FortiSandbox
FortiWeb
Syslog
Unmanaged_Devices
others
rootp
```

The list is editable: remove an entry to monitor that ADOM, add other names,
clear the list, or disable the option. Matching is exact and case-sensitive.
Names absent from the appliance have no effect. Other visible ADOMs, including
`root` and `test`, remain eligible for discovery.

Exclusions apply to ADOM-specific collection and discovery. The collector
records which configured names matched the returned ADOM list. Global system,
license, managed-device, support and resource measurements continue to describe
the whole appliance; their values are not reduced by the exclusion list.

Excluded ADOMs receive no device-list query and no ADOM device-count service
is discovered for them. Device-list failures for ADOMs still in the monitoring
scope remain visible as errors.

### Existing rules and services

Updating the package does not add or replace exclusions in existing rules.
Saved custom lists stay unchanged, and empty or disabled lists remain empty
or disabled. To use the default exclusions in an existing rule:

1. Open the rule and enable its ADOM exclusion option if necessary.
2. Enter the names listed above, keeping any additional exclusions you need.
3. Save the rule and activate changes.
4. Run **Rescan** on the affected host, then select **Remove vanished services**
   to remove ADOM services that are no longer monitored.

New-rule prefill uses `ListExtended.prefill`. The outer `DictionaryExtended`
receives `default_checked` only when that field exists in
`DictionaryExtended.__dataclass_fields__` (Checkmk 2.5). With the Checkmk 2.4
constructor, no additional default parameters are passed.
