# Authentication and API access

[← README](../README.md) · [Installation](installation.md) · [Authentication](authentication.md) · [Monitoring](monitoring.md) · [Development](development.md)

For supported services, see the [Admin user / API user comparison](../README.md#admin-user-vs-api-user).

## Required account and permissions

Use a dedicated account with JSON-RPC read access and access to every monitored
ADOM. The required admin profile depends on the FortiManager version and GUI
endpoints. Restricted profiles may deny GUI proxy access, which is reported
as an error.

### Authentication methods

The **Authentication method** option offers:

| Method | FortiManager account | Rule credentials |
| --- | --- | --- |
| **Admin user** (default) | Regular administrator with JSON API access | Username and password |
| **API user** | REST API Admin | Generated API token; username is unused |

The selection defaults to **Admin user**. Its API username and password fields
appear directly below it. **API user** displays an API token field instead.
Saved credentials are migrated into the selected method automatically.
Existing rules without this option retain password authentication. To switch an
existing rule to a REST API Admin, under **Authentication method** select
**API user**, and replace the stored password with the generated token in
**API token**. Activate changes and rescan the host.

Token authentication sends `Authorization: Bearer <token>` on every request.
No `/sys/login/user` or `/sys/logout` request is made in this mode. The token
uses the same Checkmk secret-reference mechanism as passwords and is never
placed directly in process arguments, URLs or request bodies. In FortiManager,
configure the API administrator's Trusted Hosts for the source address of the
Checkmk server, JSON API read access and access to all monitored ADOMs. See
[Fortinet's API administrator documentation](https://docs.fortinet.com/document/fortimanager/7.6.5/administration-guide/797124/creating-administrators-for-the-fortimanager-api).

API user mode does not query any `/gui/sys/` endpoints or the GUI proxy.
It monitors system information and ADOM device counts through JSON-RPC.
**FortiManager Device License**, **FortiManager Managed Devices**,
**FortiManager Resources** and **FortiManager Support** are not discovered in
this mode. Skipping these queries does not produce an API error. Admin user
mode continues to collect all services, including GUI proxy data.

After switching an existing host to API user, activate changes, rescan the host
and choose **Remove vanished services** to remove those four services. Until
removed, previously monitored services report that GUI endpoints are unavailable
with API token authentication.

### Admin user login and session lifecycle

Configure the dedicated account's username and password in the **FortiManager**
rule with **Admin user** selected. In this mode, the collector authenticates
with a password on each run. `Client.login()` sends an HTTPS POST to `/jsonrpc` with this body
(placeholder credentials):

```json
{
  "id": 1,
  "method": "exec",
  "params": [{
    "url": "/sys/login/user",
    "data": {"user": "svc.monitoring", "passwd": "<password>"}
  }]
}
```

The response must contain a successful `result.status.code` (`0`, also accepted
as the string `"0"`) and a non-empty top-level `session` string. For example:

```json
{"result": [{"status": {"code": 0}}], "session": "<session-id>"}
```

`Client.call()` includes that session in subsequent JSON-RPC request bodies.
GUI proxy requests use the `CURRENT_SESSION` cookie instead. `collect()`
requests logout in its `finally` block, and `Client.logout()` clears the local
session even if the logout request fails. A failed login stops data collection
and appears in the API service and affected monitoring services.

### API endpoints

The agent uses these endpoints:

| HTTPS path | Method | API URL |
| --- | --- | --- |
| `/jsonrpc` | `exec` | `/sys/login/user` |
| `/jsonrpc` | `get` | `/sys/status` |
| `/cgi-bin/module/flatui_proxy` | `get` | `/gui/sys/license` |
| `/cgi-bin/module/flatui_proxy` | `get` | `/gui/sys/resource/realtime` |
| `/jsonrpc` | `get` | `/dvmdb/adom` |
| `/jsonrpc` | `get` | `/dvmdb/adom/<URL-encoded name>/device` |
| `/jsonrpc` | `exec` | `/sys/logout` |

For **Admin user**, all calls are HTTPS POST requests. `/jsonrpc` uses a JSON-RPC body with
`params`, request ID and session. The GUI proxy uses a flat body such as
`{"method":"get","url":"/gui/sys/license"}` or the resource URL. Its session
is passed as the `CURRENT_SESSION` cookie. Logout runs in a `finally` block,
including after partial failures. If FortiManager does not respond to logout,
the API service reports it; the plugin cannot guarantee server-side closure.

Both modes expect responses containing `result` with an object, `status.code = 0` and
`data`. Admin user login returns a top-level `session`. Object data may be wrapped in a
single-element list; ADOM and device responses must be lists of objects.
Missing data is not treated as an empty list. Each ADOM device list is counted
in full. Firmware using pagination or different response structures requires
collector adjustments.

GUI proxy endpoints depend on firmware. The tested firmware versions are listed
under [Tested environments](../README.md#tested-environments). For UNKNOWN states,
check the API service, account permissions and response fields first. Invalid
values are not replaced with fabricated zeros.

## Error handling and password protection

- Configure the authentication method and password or token in the FortiManager
  rule (plus a username for Admin user). Checkmk supplies the secret to the
  agent through a secret reference; credentials
  do not need to be added to plugin files.
- Plaintext passwords and tokens are not passed in process arguments, and API responses
  are not dumped into service output.
- HTTP, TLS, timeout, JSON-RPC and missing-field errors produce error states.
  Failed queries do not produce fabricated measurements.
- Partial API failures preserve successfully collected sections.
- TLS certificates use Python's trust store by default; verification can be
  explicitly disabled.
- Redirects are not followed. Environment proxies are ignored.

### ADOM device counts and partial results

- A valid empty ADOM device list produces `devices=0`. A query failure produces
  UNKNOWN without a `devices` metric.
- Successful ADOMs remain usable when another ADOM fails.
- Device counts cover ADOMs visible to the API user, minus explicit exclusions.
  The user therefore needs access to every ADOM intended for monitoring.
- ADOM requests run sequentially. Each returned device list is counted in full;
  firmware using pagination requires collector adjustments.
- In Admin user mode, logout runs in `finally`. A logout failure is reported by the API service;
  the server-side session cannot be guaranteed closed without a response.

The timeout applies per request. An Admin user run makes
`6 + number of monitored ADOMs` requests, including login and logout. An API user
run makes `2 + number of monitored ADOMs` requests. Allow for this in the Checkmk data source
time limit when monitoring many ADOMs.
