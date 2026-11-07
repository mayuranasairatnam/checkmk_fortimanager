# Services, metrics and thresholds

[← README](../README.md) · [Installation](installation.md) · [Authentication](authentication.md) · [Monitoring](monitoring.md) · [Development](development.md)

The service and metric descriptions below cover the full **Admin user** scope.
**API user** collects only system information, ADOM device counts and API status.
See the [service comparison](../README.md#admin-user-vs-api-user).

## Monitoring scope and services

The special agent reads system, license, support, managed-device and resource
data through HTTPS JSON-RPC and the GUI proxy. It discovers one device-count
service for each monitored ADOM, including ADOMs with a valid empty device list.
Graphs record the exported performance metrics at normal Checkmk intervals.


| Service | Data / performance metrics |
| --- | --- |
| FortiManager System &lt;Field&gt; | Seven dedicated services: HA Mode, Hostname, Max Number of Admin Domains, Max Number of Device Groups, Platform Type, Serial Number and Version; capacity metrics `fmg_max_adoms`, `fmg_max_device_groups` |
| FortiManager Device License | `used_devices`, `licensed_devices`, `free_devices`, `utilization_percent` |
| FortiManager Managed Devices | `fmg_fortigates`, `fmg_fortiap`, `fmg_fortiswitch`, `fmg_fortiextender` |
| FortiManager ADOM &lt;Name&gt; Devices | `devices`; one service per ADOM, including empty ADOMs |
| FortiManager Support | API status, expiry date, `fmg_support_days` |
| FortiManager Resources | `fmg_cpu_percent`, `fmg_disk_percent`, `fmg_memory_percent`, `fmg_memory_used`, `fmg_memory_total`, `fmg_memory_free` |
| FortiManager API | Additional service for query errors and failed logout |

System information uses dedicated services whose OK summaries contain the
individual API value, such as `CH-FMG-001` or `10000`. Resources are displayed
in one combined service. Separate hardware/software inventory is not included.

Historical graphs use Checkmk's normal recording from the start of monitoring.
Existing FortiManager time series are not imported. The package contains metric
definitions, combined and individual graphs, and a license perfometer.

## Rules and defaults

| Rule | Default WARN / CRIT |
| --- | --- |
| FortiManager device license utilization | 80 / 90% |
| FortiManager resources: CPU | 80 / 90% |
| FortiManager resources: memory | 80 / 90% |
| FortiManager resources: disk | 80 / 90% |
| FortiManager support expiration | Below 30 / 14 days |

### Device license calculation

The collector reads `/gui/sys/license` through the GUI proxy. The
**FortiManager Device License** check maps its fields as follows:

| API field / calculation | Metric | Meaning |
| --- | --- | --- |
| `current_num_dev` | `used_devices` | Used device capacity |
| `max_num_dev` | `licensed_devices` | Licensed device capacity |
| `max_num_dev - current_num_dev` | `free_devices` | Remaining device capacity |
| `current_num_dev / max_num_dev * 100` | `utilization_percent` | Device license utilization |

For example, 8 used devices and a capacity of 10 produce 2 free devices and
80% utilization, reaching the default WARN threshold. Missing or invalid
capacity fields produce UNKNOWN. The check uses the appliance's capacity
fields directly; it does not calculate license usage by adding up ADOM device
counts or the individual managed-device types. Support status and expiry are
evaluated separately by **FortiManager Support**.

Exceeded license capacity and expired support always cause CRIT. Zero capacity
prevents percentage calculation: the result is CRIT with devices in use,
otherwise UNKNOWN. Negative free capacity during overuse is retained.

The **FortiManager resources** rule defines the unit of `memory_used` and
`memory_total`: **KiB** by default, with bytes or MiB as alternatives. Verify
that assumption against the firmware or GUI. Exported memory metrics are always
bytes. CPU, disk and memory percentages come from the corresponding API fields.

Support uses `licenses.FMWR`, falling back to `licenses.FCEM` if FMWR is absent.
Valid statuses are `valid`, `active`, `licensed` and `ok`, ignoring case.
`expired`, `invalid`, `unlicensed` and `disabled` cause CRIT. Other values are
UNKNOWN unless configured as valid after their meaning has been verified.

Expiry dates are extracted from `txt` in these formats: `YYYY-MM-DD`,
`YYYY/MM/DD`, `DD-Mon-YYYY` or `Mon DD, YYYY`. Unsupported dates produce UNKNOWN.
Remaining days use the Checkmk server's UTC calendar date.

If `dev_num_count.fex_cnt` is absent, Managed Devices reports
**not reported by API** without inventing a FortiExtender measurement. A present
but invalid value remains UNKNOWN. The combined Managed Devices graph treats
the FortiExtender metric as optional.

Graphs cover license counts and utilization, ADOM device counts, managed-device
types, resources and memory.
