# API-based Checkmk Plugin for FortiManager

[<img src="docs/assets/octicons/download-16.svg" width="16" height="16" alt=""> Download MKP](https://github.com/networkautomation-ch/checkmk_fortimanager/releases/latest) · [<img src="docs/assets/octicons/book-16.svg" width="16" height="16" alt=""> Installation](#installation)

[<img src="docs/assets/octicons/bug-16.svg" width="16" height="16" alt=""> Report a Bug](https://github.com/networkautomation-ch/checkmk_fortimanager/issues/new?title=Bug%3A%20) · [<img src="docs/assets/octicons/light-bulb-16.svg" width="16" height="16" alt=""> Request a Feature](https://github.com/networkautomation-ch/checkmk_fortimanager/issues/new?title=Feature%3A%20) · [<img src="docs/assets/octicons/git-pull-request-16.svg" width="16" height="16" alt=""> Contribute](CONTRIBUTING.md)

---

Author: **Mayuran Asairatnam** · Package: **check_fortimanager**

Monitor FortiManager through a native Checkmk special agent. No agent needs to
be installed on the appliance. Choose **Admin user** for all supported services
or **API user** for system information and ADOM device counts using an API token.

## Admin user vs API user

| Service / function | Admin user (default) | API user |
| --- | --- | --- |
| Credentials | API user name and password | API token only |
| FortiManager System Hostname | Yes | Yes |
| FortiManager System Version | Yes | Yes |
| FortiManager System Serial Number | Yes | Yes |
| FortiManager System Platform Type | Yes | Yes |
| FortiManager System HA Mode | Yes | Yes |
| FortiManager System Max Number of Admin Domains | Yes | Yes |
| FortiManager System Max Number of Device Groups | Yes | Yes |
| FortiManager ADOM &lt;Name&gt; Devices — device count per ADOM | Yes | Yes |
| FortiManager API — query status | Yes | Yes |
| FortiManager Device License | Yes | Not collected |
| FortiManager Managed Devices — counts by device type | Yes | Not collected |
| FortiManager Resources — CPU, memory and disk | Yes | Not collected |
| FortiManager Support — status and expiration | Yes | Not collected |
| ADOM exclusions | Yes | Yes |
| Graphs for collected metrics | Yes | Yes; system capacity and ADOM counts |
| Session login / logout | Yes | No; Bearer token |
| `/gui/sys/` queries through the GUI proxy | Yes | No |

API user mode skips GUI queries and does not discover the four dependent
services. After switching an existing host to **API user**, run **Rescan →
Remove vanished services** to remove them. The [authentication guide](docs/authentication.md)
explains credentials, permissions and session handling.

## Installation

1. Download and enable the MKP under **Setup → Maintenance → Extension packages**.
2. Create the monitoring host with **Configured API integrations, no Checkmk agent**.
3. In **Setup**, search for **FortiManager**, create an integration rule and restrict it to the host.
4. Enter the required credentials and review the monitoring scope and connection settings.
5. Save the rule, activate changes, run service discovery and accept the services.

See [installation](docs/installation.md) for the exact fields and defaults,
[authentication](docs/authentication.md) for account permissions, and
[monitoring](docs/monitoring.md) for services and thresholds.

## Tested environments

| Component | Tested versions |
| --- | --- |
| FortiManager | 7.6.7, 7.6.8 |
| Checkmk | 2.4, 2.5 |

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](docs/installation.md) | Host setup, connection settings, discovery and ADOM exclusions |
| [Authentication and API access](docs/authentication.md) | Admin/API users, permissions, endpoints, credential protection and errors |
| [Monitoring reference](docs/monitoring.md) | Services, metrics, thresholds, license calculations and graphs |
| [Development](docs/development.md) | Source layout, offline tests, MKP builds and CI releases |

## Contributing and license

Independent community plugin. Not affiliated with or endorsed by Fortinet.

See the [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md).
Licensed under [GPL-2.0-or-later](LICENSE). Copyright (C) 2026 Mayuran Asairatnam.
Provided without warranty; appliance licenses/support are separate from this software license.

Icons: [GitHub Octicons](https://github.com/primer/octicons), licensed under [MIT](docs/assets/octicons/LICENSE).
