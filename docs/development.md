# Development, tests and releases

[← README](../README.md) · [Installation](installation.md) · [Authentication](authentication.md) · [Monitoring](monitoring.md) · [Development](development.md)

## Source layout, tests and reproducible package build

Sources live under `cmk_addons_plugins/fortimanager/`.
`cmk_addons/plugins` is a symlink to `../cmk_addons_plugins`, enabling local
imports through `cmk_addons.plugins.fortimanager`. Only `cmk_addons_plugins`
is packaged; the import symlink is excluded.

| File | Purpose |
| --- | --- |
| `libexec/agent_fortimanager` | HTTPS client, login/logout, API collection and agent section output |
| `server_side_calls/fortimanager.py` | Builds the special-agent command from the host and rule settings, including password references |
| `rulesets/special_agent.py` | Connection settings, credentials and ADOM exclusions in Setup |
| `rulesets/check_parameters.py` | Configurable monitoring thresholds and units |
| `graphing/fortimanager.py` | Metrics, graphs and license perfometer |
| `agent_based/fortimanager.py` | Compatibility imports for checks compiled before the module split |
| `agent_based/fortimanager_api.py` | JSON parser and API status |
| `agent_based/fortimanager_system.py` | System identity and capacity |
| `agent_based/fortimanager_license.py` | Device license capacity and utilization |
| `agent_based/fortimanager_managed.py` | Managed device counts by type |
| `agent_based/fortimanager_adoms.py` | Device count per ADOM |
| `agent_based/fortimanager_support.py` | Support status and expiry |
| `agent_based/fortimanager_resources.py` | CPU, memory and disk |
| `lib/common.py` | Shared validation, numeric conversion and singleton discovery |

All checks continue to consume the shared `fortimanager` agent section.
Splitting the modules does not change service names or plugin IDs.

The data flow is: the Setup rule supplies connection settings, the server-side
call starts the collector, and the collector fetches API data using the selected
authentication method. Admin user mode logs in and out; API user mode uses a token. It then emits the JSON agent section. The parser validates that section;
the individual checks discover services and produce states and metrics.

From the project directory:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B build_mkp.py
```

Offline tests cover HTTP/JSON-RPC handling, session cookies, logout,
Bearer headers, token collection without GUI queries or login/logout,
authentication-specific discovery, secret-reference forwarding,
authentication errors, partial failures, empty ADOMs, ADOM name encoding,
missing values, license calculations, support expiry, memory units, plugin
registration and package contents, including the executable special agent.
They also model both extended dictionary constructors and verify that saved,
empty and disabled exclusion lists remain unchanged.

Without a local Checkmk installation, tests use API doubles. These do not
replace installation and discovery in a real site. Firmware-specific GUI
endpoints, memory units and account permissions must match the target appliance.
Package construction requires no external dependencies and excludes tests
and Python caches.

## CI and releases

GitHub Actions runs the offline tests and builds the MKP for pull requests and
pushes to `main`. After successful checks on `main`, CI creates a Git tag and
GitHub Release with the matching MKP attached. The first release is `v1.0.0`
with `check_fortimanager-1.0.0.mkp`; subsequent releases increment the highest
stable version tag's patch number (`v1.0.1`, `v1.0.2`, ...). Rerunning a release
for an already tagged commit reuses its version and replaces the release asset.
The release job uses the automatic `GITHUB_TOKEN` with `contents: write`.

Download installable packages from the repository's
[GitHub Releases](https://github.com/mayuranasairatnam/checkmk_fortimanager/releases).
Generated MKPs are ignored by Git. Local builds default to `1.0.2`; to build a
specific release version, run:

```sh
python3 -B build_mkp.py --version 1.0.2
```

For a standalone API test, the agent can read its password from stdin:

```sh
python3 cmk_addons_plugins/fortimanager/libexec/agent_fortimanager \
  --address fmg.example.org --user monitoring --password-stdin
```

For an API user, read the generated token from stdin instead:

```sh
python3 cmk_addons_plugins/fortimanager/libexec/agent_fortimanager \
  --address fmg.example.org --api-token-stdin
```

Supply the secret through stdin for terminal tests. Use the Checkmk rule
for production operation.

## References

- [Checkmk special agents](https://docs.checkmk.com/latest/en/devel_special_agents.html)
- [Server-side Calls API](https://docs.checkmk.com/plugin-api/latest/cmk.server_side_calls/)
- [Rulesets API](https://docs.checkmk.com/plugin-api/latest/cmk.rulesets/v1.form_specs.html)
- [Graphing API v1](https://docs.checkmk.com/plugin-api/master/cmk.graphing/v1.graphs.html)

## Lint checks

The CI workflow defines Ruff and yamllint versions and rules directly in
`.github/workflows/ci.yml`. To repeat these checks locally, install the
listed tools and run the commands from the corresponding workflow steps.
Ruff includes extensionless `libexec/agent_*` scripts.
