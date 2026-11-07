"""
Offline regression tests. Small API doubles are used when Checkmk is absent.

Transport, collector and check behavior are tested; doubles do not prove that
Checkmk can load the package. Run discovery on the target site as documented.
"""
import ast
import copy
from datetime import datetime, timedelta, timezone
from enum import IntEnum
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import types
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
FAMILY = ROOT / 'cmk_addons_plugins' / 'fortimanager'


def load(name, path):
    """
    Load a Python module from a source file, including extensionless agents.

    Input:
        name: Name assigned to the object being created.
        path: Path to the Python source file.

    Output:
        Imported module object after executing its source.

    """
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


try:
    importlib.import_module('cmk.agent_based.v2')
except ImportError:
    class State(IntEnum):
        """
        Offline stand-in for Checkmk monitoring states.

        Input:
            Constructor arguments supported by the base class.

        Output:
            State instance.

        """
        OK = 0
        WARN = 1
        CRIT = 2
        UNKNOWN = 3

    class Record:
        """
        Attribute container used by the offline Checkmk API doubles.

        Input:
            **kwargs: Attributes stored on the record.

        Output:
            Record instance.

        """
        def __init__(self, **kwargs):
            """
            Initialize the Record instance.

            Input:
                kwargs: Attribute names and values stored on the test double.

            Output:
                None; initializes instance attributes for subsequent operations.

            """
            self.__dict__.update(kwargs)

    class Metric(Record):
        """
        Offline Checkmk metric record containing a name and value.

        Input:
            name: Name assigned to the object being created.
            value: Raw value to validate or convert.
            **kwargs: Attributes stored on the record.

        Output:
            Metric instance.

        """
        def __init__(self, name, value, **kwargs):
            """
            Initialize the Metric instance.

            Input:
                name: Name assigned to the object being created.
                value: Raw value to validate or convert.
                kwargs: Attribute names and values stored on the test double.

            Output:
                None; initializes instance attributes for subsequent operations.

            """
            super().__init__(name=name, value=value, **kwargs)

    class Result(Record):
        """
        Offline Checkmk result record containing state and output text.

        Input:
            Constructor arguments supported by the base class.

        Output:
            Result instance.

        """
        pass

    def check_levels(value, levels_upper=None, levels_lower=None, metric_name=None, label='', render_func=str, **kwargs):
        """
        Apply fixed warning and critical levels in the offline API double.

        Input:
            value: Raw value to validate or convert.
            levels_upper: Upper warning and critical levels in Checkmk format.
            levels_lower: Lower warning and critical levels in Checkmk format.
            metric_name: Metric name, or None to omit the metric.
            label: Human-readable label for the output.
            render_func: Callable formatting the measured value for the summary.
            kwargs: Additional keyword arguments forwarded to the operation.

        Output:
            Yields a Result and, when requested, a Metric for the supplied value.

        """
        state = State.OK
        for levels, lower in ((levels_upper, False), (levels_lower, True)):
            if levels and levels[0] == 'fixed':
                warn, crit = levels[1]
                if (value < crit if lower else value >= crit):
                    state = max(state, State.CRIT)
                elif (value < warn if lower else value >= warn):
                    state = max(state, State.WARN)
        yield Result(state=state, summary=f'{label}: {render_func(value)}')
        if metric_name:
            yield Metric(metric_name, value)

    api = types.ModuleType('cmk.agent_based.v2')
    for name, value in {'AgentSection': Record, 'CheckPlugin': Record, 'Metric': Metric,
                        'Result': Result, 'Service': Record, 'State': State,
                        'check_levels': check_levels, 'render': types.SimpleNamespace(
                            percent=lambda v: f'{v:.1f}%', bytes=lambda v: f'{v} B')}.items():
        setattr(api, name, value)
    for name in ('cmk', 'cmk.agent_based'):
        sys.modules[name] = types.ModuleType(name)
    sys.modules['cmk.agent_based.v2'] = api

agent = load('fmg_agent', FAMILY / 'libexec' / 'agent_fortimanager')
check_types = importlib.import_module('cmk.agent_based.v2')

# Resolve the plugin namespace through the same import link used during development.
sys.path.insert(0, str(ROOT))
from cmk_addons.plugins.fortimanager.lib import common  # noqa: E402 - Install Checkmk API doubles first.
from cmk_addons.plugins.fortimanager.agent_based import (  # noqa: E402 - Install Checkmk API doubles first.
    fortimanager as legacy_checks,
    fortimanager_api as api_checks,
    fortimanager_system as system_checks,
    fortimanager_license as license_checks,
    fortimanager_managed as managed_checks,
    fortimanager_adoms as adoms_checks,
    fortimanager_support as support_checks,
    fortimanager_resources as resources_checks,
)

CHECK_MODULES = (
    legacy_checks,
    api_checks,
    system_checks,
    license_checks,
    managed_checks,
    adoms_checks,
    support_checks,
    resources_checks,
)
builder = load('fmg_build', ROOT / 'build_mkp.py')


LICENSE = {'current_num_dev': 8, 'max_num_dev': 10,
           'dev_num_count': {k: {'val': v} for k, v in (
               ('fgt_cnt', 8), ('fap_cnt', 0), ('fsw_cnt', 2), ('fex_cnt', 0))},
           'licenses': {'FMWR': {'status': 'Valid', 'txt': 'Expires on 2099-01-01'}}}
RESOURCES = {'cpu_avg': 12, 'disk': 20, 'memory': 50, 'memory_used': 512, 'memory_total': 1024}
SYSTEM = {key: ('0' if key == 'HA Mode' else 'value') for key in agent.SYSTEM_KEYS}
SYSTEM.update({'Max Number of Admin Domains': 2, 'Max Number of Device Groups': 3})

# Sanitized FortiManager 7.6 GUI response: FCEM support, no fex_cnt.
LICENSE_76 = {
    'current_num_dev': 3, 'max_num_dev': 3,
    'dev_num_count': {'fap_cnt': {'label': 'FortiAPs', 'val': 4},
                      'fgt_cnt': {'label': 'FortiGates/Logging Devices', 'val': 3},
                      'fsw_cnt': {'label': 'FortiSwitches', 'val': 1}},
    'licenses': {'FCEM': {'css': 'ok', 'status': 'ok',
                          'txt': 'Web/Online Support (Expires 2028-06-14)'}},
}


class FakeClient:
    """
    Fixture API client supporting deterministic responses and failures.

    Input:
        failures: Fixture overrides used to simulate API failures.

    Output:
        FakeClient instance.

    """
    def __init__(self, failures=None):
        """
        Initialize the FakeClient instance.

        Input:
            failures: Fixture overrides used to simulate API failures.

        Output:
            None; initializes instance attributes for subsequent operations.

        """
        self.failures = failures or {}
        self.calls = []
        self.logged_out = False

    def login(self, user, password):
        """
        Record or simulate authentication in the fixture client.

        Input:
            user: Account name used for authentication.
            password: Password used for authentication.

        Output:
            None; updates fixture authentication state or raises the configured error.

        """
        self.calls.append('login')
        if 'login' in self.failures:
            raise agent.APIError(self.failures['login'])

    def logout(self):
        """
        Record or simulate session cleanup in the fixture client.

        Input:
            Current instance state.

        Output:
            None; updates fixture logout state or raises the configured error.

        """
        self.logged_out = True
        if 'logout' in self.failures:
            raise agent.APIError(self.failures['logout'])

    def call(self, url, **kwargs):
        """
        Return a fixture response or simulate a configured API failure.

        Input:
            url: API resource path.
            kwargs: Additional keyword arguments forwarded to the operation.

        Output:
            Deep copy of the fixture response, or raises the configured API error.

        """
        self.calls.append((url, kwargs))
        if url in self.failures:
            failure = self.failures[url]
            if isinstance(failure, str):
                raise agent.APIError(failure)
            return failure
        return copy.deepcopy({
            '/sys/status': SYSTEM, '/gui/sys/license': LICENSE,
            '/gui/sys/resource/realtime': RESOURCES,
            '/dvmdb/adom': [{'name': 'empty'}, {'name': 'production / 7.4'}],
            '/dvmdb/adom/empty/device': [],
            '/dvmdb/adom/production%20%2F%207.4/device': [{'name': 'fgt1'}],
        }[url])


def section(client=None):
    """
    Build parsed section data from the fixture API client.

    Input:
        client: Client used to obtain API or SSH data.

    Output:
        Collected section mapping for use by the check tests.

    """
    return agent.collect(client or FakeClient(), 'test-user', 'test-password')


def metrics(results):
    """
    Index emitted metrics by their names.

    Input:
        results: Check results or collected section records to process.

    Output:
        Mapping of metric names to their measured values.

    """
    return {r.name: r.value for r in results if isinstance(r, check_types.Metric)}


def states(results):
    """
    Extract monitoring states from emitted results.

    Input:
        results: Check results or collected section records to process.

    Output:
        List of states from Result objects.

    """
    return [r.state for r in results if isinstance(r, check_types.Result)]


class CollectorTests(unittest.TestCase):
    """
    Regression tests for Collector.

    Input:
        Test method selected by the unittest runner.

    Output:
        CollectorTests instance.

    """
    def test_excluded_adoms_are_not_queried_or_discovered(self):
        """
        Exclude selected ADOMs without hiding failures in the remaining scope.

        Input:
            Fixture ADOMs with an excluded failing endpoint and retained root/test ADOMs.

        Output:
            None; assertions verify query scope, discovery and explicit exclusion metadata.

        """
        overrides = {
            '/dvmdb/adom': [{'name': 'FortiWeb'}, {'name': 'root'}, {'name': 'test'}],
            '/dvmdb/adom/FortiWeb/device': 'must not be queried',
            '/dvmdb/adom/root/device': [{'name': 'firewall'}],
            '/dvmdb/adom/test/device': [],
        }
        client = FakeClient(overrides)
        data = agent.collect(client, 'test-user', 'test-password', ('FortiWeb', 'others'))
        self.assertEqual(data['adoms']['excluded'], ['FortiWeb'])
        self.assertEqual([service.item for service in adoms_checks.discover_adoms(data)], ['root', 'test'])
        self.assertEqual(data['api']['errors'], [])
        self.assertFalse(any(isinstance(call, tuple) and call[0] == '/dvmdb/adom/FortiWeb/device'
                             for call in client.calls))
        failed = agent.collect(FakeClient(dict(overrides, **{'/dvmdb/adom/root/device': 'timeout'})),
                               'test-user', 'test-password', ('FortiWeb',))
        self.assertEqual(failed['adoms']['data']['root']['error'], 'timeout')
        self.assertTrue(failed['api']['errors'])
        empty = agent.collect(FakeClient(overrides), 'test-user', 'test-password',
                              ('FortiWeb', 'root', 'test'))
        self.assertEqual(empty['adoms']['data'], {})
        self.assertEqual(empty['api']['errors'], [])
        self.assertEqual(list(adoms_checks.discover_adoms(empty)), [])

    def test_cli_passes_adom_exclusions_to_collector(self):
        """
        Forward repeated exclusion options from the standalone agent CLI.

        Input:
            Command-line exclusions and a mocked collector.

        Output:
            None; assertions verify exact exclusion names reach the collector.

        """
        with patch.object(agent, 'Client', return_value=FakeClient()), \
                patch.object(agent, 'collect', return_value={}) as collect, \
                patch.object(agent.sys, 'stdin', io.StringIO('test-password\n')), \
                patch('sys.stdout', io.StringIO()):
            self.assertEqual(agent.main([
                '--address', 'fmg.example', '--user', 'monitoring', '--password-stdin',
                '--exclude-adom', 'FortiWeb', '--exclude-adom', 'rootp',
            ]), 0)
        self.assertEqual(collect.call_args.args[3], ['FortiWeb', 'rootp'])

    def test_success_and_logout(self):
        """
        Verify success and logout.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        client = FakeClient()
        data = section(client)
        self.assertTrue(client.logged_out)
        self.assertEqual(data['api']['errors'], [])
        self.assertEqual(data['adoms']['data']['empty']['count'], 0)
        self.assertEqual(data['adoms']['data']['production / 7.4']['count'], 1)

    def test_auth_error_closes_session_and_emits_no_metrics(self):
        """
        Verify auth error closes session and emits no metrics.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        client = FakeClient({'login': 'denied'})
        data = section(client)
        self.assertTrue(client.logged_out)
        self.assertEqual(client.calls, ['login'])
        self.assertTrue(data['api']['errors'])
        result = list(license_checks.check_license({'levels': ('fixed', (80, 90))}, data))
        self.assertEqual(metrics(result), {})
        self.assertIn(check_types.State.UNKNOWN, states(result))

    def test_adom_failure_is_never_zero(self):
        """
        Verify ADOM failure is never zero.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/dvmdb/adom/empty/device': 'timeout'}))
        self.assertEqual([s.item for s in adoms_checks.discover_adoms(data)], ['empty', 'production / 7.4'])
        result = list(adoms_checks.check_adoms('empty', data))
        self.assertEqual(metrics(result), {})
        self.assertIn(check_types.State.UNKNOWN, states(result))

    def test_empty_adom_is_valid_zero(self):
        """
        Verify empty ADOM is valid zero.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        self.assertEqual(metrics(list(adoms_checks.check_adoms('empty', section()))), {'devices': 0})

    def test_gui_service_discovery_preserves_admin_errors(self):
        for data in (section(), section(FakeClient({'login': 'denied'})),
                     section(FakeClient({'/gui/sys/license': 'HTTP 400',
                                         '/gui/sys/resource/realtime': 'HTTP 400'}))):
            for module in (license_checks, managed_checks, support_checks, resources_checks):
                plugin = next(value for name, value in vars(module).items()
                              if name.startswith('check_plugin_'))
                self.assertEqual(len(list(plugin.discovery_function(data))), 1)

    def test_partial_failure_preserves_other_sections(self):
        """
        Verify partial failure preserves other sections.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/gui/sys/license': 'HTTP 403'}))
        self.assertEqual(data['resources']['data'], RESOURCES)
        self.assertIn(check_types.State.CRIT, states(list(api_checks.check_api(data))))

    def test_failed_adom_list_and_disappeared_adom(self):
        """
        Verify failed ADOM list and disappeared ADOM.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/dvmdb/adom': 'API error'}))
        self.assertEqual(list(adoms_checks.discover_adoms(data)), [])
        self.assertEqual(metrics(list(adoms_checks.check_adoms('empty', data))), {})
        self.assertIn(check_types.State.UNKNOWN, states(list(adoms_checks.check_adoms('removed', section()))))

    def test_invalid_list_is_error_and_logout_failure_reported(self):
        """
        Verify invalid list is error and logout failure reported.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/dvmdb/adom': {}, 'logout': 'timeout'}))
        self.assertIn('error', data['adoms'])
        self.assertTrue(any('Logout failed' in error for error in data['api']['errors']))

    def test_json_serialization_preserves_adom_names(self):
        """
        Verify json serialization preserves ADOM names.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        original = section()
        self.assertEqual(api_checks.parse_fortimanager([[json.dumps(original)]]), original)
        self.assertTrue(api_checks.parse_fortimanager([['invalid']])['api']['errors'])


class TransportTests(unittest.TestCase):
    """
    Regression tests for Transport.

    Input:
        Test method selected by the unittest runner.

    Output:
        TransportTests instance.

    """
    def client(self, payload):
        """
        Create a transport client with the supplied fake response.

        Input:
            payload: API response payload.

        Output:
            API client configured with a mock opener.

        """
        client = agent.Client('fortimanager.example')
        self.requests = []

        def response(request, timeout):
            """
            Supply a deterministic HTTP response for the transport test.

            Input:
                request: HTTP request supplied to the transport double.
                timeout: Maximum wait time in seconds.

            Output:
                Context manager or response double used by the mocked opener.

            """
            self.requests.append(request)
            if isinstance(payload, Exception):
                raise payload
            return io.BytesIO(json.dumps(payload).encode())

        client.opener = types.SimpleNamespace(open=response)
        return client

    def test_token_collection_skips_login_logout_and_authenticates_all_requests(self):
        client = self.client({})
        client.api_token = 'test-api-token'

        def respond(request, timeout):
            self.requests.append(request)
            self.assertEqual(request.get_header('Authorization'), 'Bearer test-api-token')
            self.assertIsNone(request.get_header('Cookie'))
            self.assertTrue(request.full_url.endswith('/jsonrpc'))
            body = json.loads(request.data)
            self.assertNotIn('session', body)
            self.assertNotIn('test-api-token', request.full_url)
            self.assertNotIn('test-api-token', json.dumps(body))
            url = body['url'] if 'url' in body else body['params'][0]['url']
            payloads = {
                '/sys/status': SYSTEM, '/dvmdb/adom': [{'name': 'root'}],
                '/dvmdb/adom/root/device': [],
            }
            return io.BytesIO(json.dumps({'result': [{'status': {'code': 0},
                'data': payloads[url]}]}).encode())

        client.opener = types.SimpleNamespace(open=respond)
        data = agent.collect(client, None, None)
        self.assertEqual(data['api']['errors'], [])
        self.assertEqual(len(self.requests), 3)
        self.assertIn('disabled', data['license'])
        self.assertIn('disabled', data['resources'])
        self.assertEqual([service.item for service in system_checks.discover_system(data)],
                         list(system_checks.SYSTEM_FIELDS))
        self.assertEqual([service.item for service in adoms_checks.discover_adoms(data)], ['root'])
        self.assertEqual(states(list(api_checks.check_api(data))), [check_types.State.OK])
        for module in (license_checks, managed_checks, support_checks, resources_checks):
            plugin = next(value for name, value in vars(module).items()
                          if name.startswith('check_plugin_'))
            self.assertEqual(list(plugin.discovery_function(data)), [])
        self.assertIsNone(client.session)

    def test_invalid_tokens_are_rejected_without_echoing_secret(self):
        for token in ('', 'secret\r\nInjected: value', 'secret token', 'secreté'):
            with self.subTest(token=token), self.assertRaises(agent.APIError) as error:
                agent.Client('fortimanager.example', api_token=token)
            self.assertNotIn('secret', str(error.exception))

    def test_token_cli_reads_secret_from_stdin_without_username(self):
        client = self.client({'result': [{'status': {'code': -11, 'message': 'secret'}}]})
        client.api_token = 'test-api-token'
        with patch.object(agent, 'Client', return_value=client) as constructor, \
                patch.object(agent.sys, 'stdin', io.StringIO('test-api-token\n')), \
                patch.object(agent.sys, 'stdout', io.StringIO()) as output:
            self.assertEqual(agent.main(['--address', 'fmg.example', '--api-token-stdin']), 0)
        self.assertEqual(constructor.call_args.kwargs['api_token'], 'test-api-token')
        self.assertNotIn('test-api-token', output.getvalue())
        self.assertNotIn('secret', output.getvalue())
        self.assertEqual(len(self.requests), 2)

    def test_login_and_cookie_and_logout(self):
        """
        Verify login and cookie and logout.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        client = self.client({'session': 'session-test', 'result': [{'status': {'code': 0}, 'data': {}}]})
        client.login('test-user', 'test-password')
        login = json.loads(self.requests[0].data)
        self.assertEqual(login['params'][0]['data']['passwd'], 'test-password')
        client.call('/gui/sys/license', gui=True)
        self.assertEqual(self.requests[-1].get_header('Cookie'), 'CURRENT_SESSION=session-test')
        self.assertTrue(self.requests[-1].full_url.endswith('/cgi-bin/module/flatui_proxy'))
        self.assertEqual(json.loads(self.requests[-1].data), {'method': 'get', 'url': '/gui/sys/license'})
        client.call('/gui/sys/resource/realtime', gui=True)
        self.assertEqual(json.loads(self.requests[-1].data), {'method': 'get', 'url': '/gui/sys/resource/realtime'})
        client.logout()
        self.assertIsNone(client.session)
        self.assertEqual(json.loads(self.requests[-1].data)['params'][0]['url'], '/sys/logout')
        self.assertEqual(json.loads(self.requests[-1].data)['session'], 'session-test')

    def test_gui_proxy_rejects_old_envelope_regression(self):
        """
        Verify gui proxy rejects old envelope regression.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        client = agent.Client('fortimanager.example')

        def respond(request, timeout):
            """
            Supply a deterministic HTTP response for the transport test.

            Input:
                request: HTTP request supplied to the transport double.
                timeout: Maximum wait time in seconds.

            Output:
                Context manager or response double used by the mocked opener.

            """
            body = json.loads(request.data)
            if request.full_url.endswith('/jsonrpc'):
                self.assertIn('params', body)
                return io.BytesIO(json.dumps({'session': 'fake-session', 'result': [{'status': {'code': 0}}]}).encode())
            if body != {'method': 'get', 'url': '/gui/sys/license'}:
                raise HTTPError(request.full_url, 404, 'Not found', {}, None)
            self.assertEqual(request.get_header('Cookie'), 'CURRENT_SESSION=fake-session')
            return io.BytesIO(json.dumps({'result': [{'data': LICENSE_76, 'id': None,
                'status': {'code': 0, 'message': ''}, 'url': '/gui/sys/license'}]}).encode())

        client.opener = types.SimpleNamespace(open=respond)
        client.login('test-user', 'test-password')
        self.assertEqual(client.call('/gui/sys/license', gui=True), LICENSE_76)
        client.logout()

    def test_api_status_missing_and_error_and_null_data(self):
        """
        Verify API status missing and error and null data.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        for payload in ({}, {'result': [{'status': {'code': -11, 'message': 'sensitive'}}]},
                        {'result': [{'data': []}]}, {'result': [{'status': {'code': 0}, 'data': None}]}):
            with self.subTest(payload=payload), self.assertRaises(agent.APIError) as error:
                self.client(payload).call('/test')
            self.assertNotIn('sensitive', str(error.exception))

    def test_http_and_timeout(self):
        """
        Verify http and timeout.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        for exception in (HTTPError('https://host', 401, 'secret', {}, None),
                          URLError('secret'), TimeoutError('secret')):
            with self.subTest(exception=exception), self.assertRaises(agent.APIError) as error:
                self.client(exception).call('/test')
            self.assertNotIn('secret', str(error.exception))

    def test_login_without_session_fails(self):
        """
        Verify login without session fails.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        with self.assertRaises(agent.APIError):
            self.client({'result': [{'status': {'code': 0}}]}).login('u', 'p')

    def test_ipv6_address_and_tls_default(self):
        """
        Verify ipv6 address and tls default.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        self.assertEqual(agent.Client('::1').base, 'https://[::1]:443')
        with self.assertRaises(agent.APIError):
            agent.Client('https://invalid')


class CheckTests(unittest.TestCase):
    """
    Regression tests for Check.

    Input:
        Test method selected by the unittest runner.

    Output:
        CheckTests instance.

    """
    def test_license_levels_and_counts(self):
        """
        Verify license levels and counts.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        result = list(license_checks.check_license({'levels': ('fixed', (80, 90))}, section()))
        self.assertEqual(metrics(result), {'used_devices': 8, 'licensed_devices': 10,
                                           'free_devices': 2, 'utilization_percent': 80})
        self.assertIn(check_types.State.WARN, states(result))
        data = section()
        data['license']['data']['current_num_dev'] = 11
        result = list(license_checks.check_license({'levels': ('no_levels', None)}, data))
        self.assertIn(check_types.State.CRIT, states(result))

    def test_zero_capacity_not_divided_and_missing_not_zero(self):
        """
        Verify zero capacity not divided and missing not zero.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        for maximum in (0, None, -1):
            data = section()
            data['license']['data']['max_num_dev'] = maximum
            result = list(license_checks.check_license({'levels': ('fixed', (80, 90))}, data))
            self.assertNotIn('utilization_percent', metrics(result))

    def test_bad_numbers(self):
        """
        Verify bad numbers.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        for value in (True, None, 'nan', 'inf', 'unexpected', []):
            self.assertIsNone(common.number(value))
        self.assertEqual(common.number('0%'), 0)
        self.assertIsNone(common.count(1.5))

    def test_missing_managed_device_count_is_unknown(self):
        """
        Verify missing managed device count is unknown.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section()
        del data['license']['data']['dev_num_count']['fap_cnt']
        result = list(managed_checks.check_managed(data))
        self.assertIn(check_types.State.UNKNOWN, states(result))
        self.assertNotIn('fmg_fortiap', metrics(result))

    def test_resources_units_and_missing_used(self):
        """
        Verify resources units and missing used.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        params = copy.deepcopy(resources_checks.check_plugin_fortimanager_resources.check_default_parameters)
        result = list(resources_checks.check_resources(params, section()))
        self.assertEqual(metrics(result)['fmg_memory_used'], 512 * 1024)
        self.assertEqual(metrics(result)['fmg_memory_free'], 512 * 1024)
        data = section()
        del data['resources']['data']['memory_used']
        result = list(resources_checks.check_resources(params, data))
        self.assertNotIn('fmg_memory_used', metrics(result))
        self.assertEqual(metrics(result)['fmg_cpu_percent'], 12)
        self.assertIn(check_types.State.UNKNOWN, states(result))

    def test_support_dates_status_and_expiry(self):
        """
        Verify support dates status and expiry.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        self.assertEqual(support_checks.expiry_date('Registered 2020-01-01, expires on 2030-12-31').isoformat(), '2030-12-31')
        for text in ('Expiry: 2030/12/31', '31-Dec-2030', 'Dec 31, 2030'):
            self.assertEqual(support_checks.expiry_date(text).isoformat(), '2030-12-31')
        self.assertIsNone(support_checks.expiry_date('invalid'))
        params = support_checks.check_plugin_fortimanager_support.check_default_parameters
        data = section()
        data['license']['data']['licenses']['FMWR']['status'] = 1
        self.assertIn(check_types.State.UNKNOWN, states(list(support_checks.check_support(params, data))))
        params = dict(params, valid_statuses=['1'])
        self.assertEqual(set(states(list(support_checks.check_support(params, data)))), {check_types.State.OK})
        yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
        data['license']['data']['licenses']['FMWR']['txt'] = yesterday.isoformat()
        self.assertIn(check_types.State.CRIT, states(list(support_checks.check_support(params, data))))

    def test_system_missing_data_is_unknown(self):
        """
        Verify system missing data is unknown.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section()
        del data['system']['data']['Hostname']
        self.assertIn(check_types.State.UNKNOWN, states(list(system_checks.check_system('Hostname', data))))
        self.assertEqual(states(list(system_checks.check_system('Version', data))), [check_types.State.OK])

    def test_system_discovery_separate_services_and_capacity_metrics(self):
        """
        Verify system discovery separate services and capacity metrics.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section()
        self.assertEqual([s.item for s in system_checks.discover_system(data)], list(system_checks.SYSTEM_FIELDS))
        for field in system_checks.SYSTEM_FIELDS:
            self.assertEqual(set(states(list(system_checks.check_system(field, data)))), {check_types.State.OK})
        self.assertEqual(metrics(list(system_checks.check_system('Max Number of Admin Domains', data))), {'fmg_max_adoms': 2})
        self.assertEqual(metrics(list(system_checks.check_system('Max Number of Device Groups', data))), {'fmg_max_device_groups': 3})
        failed = section(FakeClient({'/sys/status': 'HTTP 403'}))
        self.assertEqual(len(list(system_checks.discover_system(failed))), 7)
        self.assertIn(check_types.State.UNKNOWN, states(list(system_checks.check_system('Hostname', failed))))
        self.assertIn(check_types.State.UNKNOWN, states(list(system_checks.check_system(None, data))))

    def test_fortimanager_76_license_managed_and_support(self):
        """
        Verify FortiManager 76 license managed and support.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/gui/sys/license': LICENSE_76}))
        result = list(license_checks.check_license({'levels': ('fixed', (80, 90))}, data))
        self.assertEqual(metrics(result), {'used_devices': 3, 'licensed_devices': 3,
                                           'free_devices': 0, 'utilization_percent': 100})
        self.assertIn(check_types.State.CRIT, states(result))
        managed = list(managed_checks.check_managed(data))
        self.assertEqual(set(states(managed)), {check_types.State.OK})
        self.assertEqual(metrics(managed), {'fmg_fortigates': 3, 'fmg_fortiap': 4, 'fmg_fortiswitch': 1})
        support = list(support_checks.check_support(support_checks.check_plugin_fortimanager_support.check_default_parameters, data))
        self.assertEqual(set(states(support)), {check_types.State.OK})
        self.assertEqual(metrics(support)['fmg_support_days'],
                         (datetime(2028, 6, 14).date() - datetime.now(timezone.utc).date()).days)

    def test_support_fmwr_preferred_and_bad_optional_count_not_hidden(self):
        """
        Verify support fmwr preferred and bad optional count not hidden.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        data = section(FakeClient({'/gui/sys/license': LICENSE_76}))
        data['license']['data']['licenses']['FMWR'] = {'status': 'expired', 'txt': 'Expires 2020-01-01'}
        support = list(support_checks.check_support(support_checks.check_plugin_fortimanager_support.check_default_parameters, data))
        self.assertIn(check_types.State.CRIT, states(support))
        data['license']['data']['dev_num_count']['fex_cnt'] = {'val': None}
        self.assertIn(check_types.State.UNKNOWN, states(list(managed_checks.check_managed(data))))


class PackageTests(unittest.TestCase):
    """
    Regression tests for Package.

    Input:
        Test method selected by the unittest runner.

    Output:
        PackageTests instance.

    """
    def test_rule_migration_removes_address_and_ca_overrides(self):
        """
        Migrate saved rules without retaining removed address or CA bundle settings.

        Input:
            Legacy rule settings with address and CA bundle overrides.

        Output:
            None; assertions verify migration, input preservation and form fields.

        """
        tree = ast.parse((FAMILY / 'rulesets' / 'special_agent.py').read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        namespace = {}
        exec(compile(ast.Module(body=[node for node in functions if node.name == 'migrate_parameters'],
                                type_ignores=[]), '<rule migration>', 'exec'), namespace)
        original = {
            'user': 'monitoring', 'password': 'password-reference',
            'address': 'old-target.example', 'port': 8443,
            'ca_file': '/obsolete/ca-bundle.pem',
        }
        snapshot = copy.deepcopy(original)
        migrated = namespace['migrate_parameters'](original)
        self.assertEqual(original, snapshot)
        self.assertNotIn('address', migrated)
        self.assertNotIn('ca_file', migrated)
        self.assertEqual(migrated['authentication'],
                         ('password', {'user': original['user'], 'password': original['password']}))
        self.assertNotIn('user', migrated)
        self.assertNotIn('password', migrated)
        self.assertEqual(namespace['migrate_parameters'](migrated), migrated)
        token_rule = dict(original, auth_method='token')
        self.assertEqual(namespace['migrate_parameters'](token_rule)['authentication'],
                         ('token', original['password']))
        self.assertEqual(migrated['port'], 8443)
        form = next(node for node in functions if node.name == 'parameter_form')
        dictionary = next(node.value for node in form.body if isinstance(node, ast.Return))
        elements = next(keyword.value for keyword in dictionary.keywords if keyword.arg == 'elements')
        self.assertNotIn('address', [ast.literal_eval(key) for key in elements.keys])
        self.assertNotIn('ca_file', [ast.literal_eval(key) for key in elements.keys])

    def test_agent_target_uses_host_configuration(self):
        """
        Ignore removed overrides and resolve the target from the Checkmk host.

        Input:
            Host configurations with or without a primary address and a saved override.

        Output:
            None; assertions verify API command arguments and secret identity.

        """
        api = types.ModuleType('cmk.server_side_calls.v1')
        api.Secret = type('Secret', (), {})
        api.SpecialAgentCommand = lambda **kwargs: types.SimpleNamespace(**kwargs)
        api.SpecialAgentConfig = lambda **kwargs: types.SimpleNamespace(**kwargs)
        api.noop_parser = lambda value: value
        with patch.dict(sys.modules, {'cmk.server_side_calls.v1': api}):
            calls = load('fmg_command_test', FAMILY / 'server_side_calls' / 'fortimanager.py')
        secret = api.Secret()
        params = {
            'user': 'monitoring', 'password': secret, 'address': 'old-target.example',
            'ca_file': '/obsolete/ca-bundle.pem',
            'exclude_adoms': ['FortiWeb', 'rootp'],
        }
        for primary, expected in (('192.0.2.10', '192.0.2.10'), ('', 'fmg.example')):
            with self.subTest(primary=primary):
                host = types.SimpleNamespace(
                    primary_ip_config=types.SimpleNamespace(address=primary), name='fmg.example',
                )
                command, = calls.commands(params, host)
                args = command.command_arguments
                self.assertEqual(args[:2], ['--address', expected])
                self.assertNotIn('old-target.example', args)
                self.assertNotIn('--ca-file', args)
                self.assertNotIn('/obsolete/ca-bundle.pem', args)
                self.assertNotIn('--no-cert-check', args)
                self.assertIs(args[args.index('--password-id') + 1], secret)
                self.assertEqual(args.count('--address'), 1)
                self.assertEqual(args.count('--exclude-adom'), 2)
                self.assertEqual([args[index + 1] for index, value in enumerate(args)
                                  if value == '--exclude-adom'], ['FortiWeb', 'rootp'])

    def test_token_command_preserves_secret_reference_and_omits_password_login(self):
        api = types.ModuleType('cmk.server_side_calls.v1')
        api.Secret = type('Secret', (), {})
        api.SpecialAgentCommand = lambda **kwargs: types.SimpleNamespace(**kwargs)
        api.SpecialAgentConfig = lambda **kwargs: types.SimpleNamespace(**kwargs)
        api.noop_parser = lambda value: value
        with patch.dict(sys.modules, {'cmk.server_side_calls.v1': api}):
            calls = load('fmg_token_command_test', FAMILY / 'server_side_calls' / 'fortimanager.py')
        secret = api.Secret()
        host = types.SimpleNamespace(primary_ip_config=types.SimpleNamespace(address='192.0.2.10'))
        params = {'auth_method': 'token', 'password': secret}
        command, = calls.commands(params, host)
        args = command.command_arguments
        self.assertIs(args[args.index('--api-token-id') + 1], secret)
        self.assertNotIn('--user', args)
        self.assertNotIn('--password-id', args)
        nested_command, = calls.commands({'authentication': ('token', secret)}, host)
        self.assertEqual(nested_command.command_arguments, args)
        nested_admin, = calls.commands({'authentication': (
            'password', {'user': 'monitoring', 'password': secret})}, host)
        self.assertIs(nested_admin.command_arguments[
            nested_admin.command_arguments.index('--password-id') + 1], secret)
        self.assertIn('monitoring', nested_admin.command_arguments)
        with self.assertRaises(TypeError):
            list(calls.commands(dict(params, password='plaintext-token'), host))
        with self.assertRaises(ValueError):
            list(calls.commands(dict(params, auth_method='password'), host))

    def test_new_rule_exclusion_defaults_preserve_existing_rules(self):
        """
        Prefill new rules while retaining saved, empty and disabled exclusions.

        Input:
            Checkmk 2.4 and 2.5 extended-form constructor contracts and saved rules.

        Output:
            None; assertions verify the requested defaults and migration behavior.

        """
        from dataclasses import make_dataclass

        expected = ['FortiAnalyzer', 'FortiAuthenticator', 'FortiCache', 'FortiCarrier', 'FortiClient', 'FortiDDoS', 'FortiDeceptor', 'FortiFirewall', 'FortiFirewallCarrier', 'FortiMail', 'FortiManager', 'FortiProxy', 'FortiSandbox', 'FortiWeb', 'Syslog', 'Unmanaged_Devices', 'others', 'rootp']
        tree = ast.parse((FAMILY / 'rulesets' / 'special_agent.py').read_text())
        definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) or (
            isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
            target.id == 'DEFAULT_EXCLUDED_ADOMS' for target in node.targets))]
        namespace = {
            'Title': str, 'Help': str,
            'DefaultValue': lambda value: types.SimpleNamespace(value=value),
            'DictElement': lambda parameter_form, required=False: types.SimpleNamespace(
                parameter_form=parameter_form, required=required),
            'validators': types.SimpleNamespace(
                LengthInRange=lambda **kwargs: None, NetworkPort=lambda: None,
                NumberInRange=lambda **kwargs: None),
            'migrate_to_password': lambda value: value,
        }
        for name in ('Dictionary', 'CascadingSingleChoice', 'CascadingSingleChoiceElement',
                     'Integer', 'Password', 'SingleChoice', 'SingleChoiceElement', 'String'):
            namespace[name] = lambda **kwargs: types.SimpleNamespace(**kwargs)
        namespace['ListExtended'] = make_dataclass('ListExtended',
            ['title', 'element_template', 'prefill', 'help_text'], kw_only=True)
        for version, extra in (('2.4', []), ('2.5', ['default_checked'])):
            with self.subTest(version=version):
                namespace['DictionaryExtended'] = make_dataclass('DictionaryExtended',
                    ['elements', 'migrate', *extra], kw_only=True)
                exec(compile(ast.Module(body=definitions, type_ignores=[]), '<rule forms>', 'exec'), namespace)
                form = namespace['parameter_form']()
                auth = form.elements['authentication'].parameter_form
                self.assertTrue(form.elements['authentication'].required)
                self.assertTrue(auth.elements[0].parameter_form.elements['user'].required)
                self.assertTrue(auth.elements[0].parameter_form.elements['password'].required)
                self.assertNotIn('user', form.elements)
                self.assertNotIn('password', form.elements)
                self.assertEqual([(entry.name, entry.title) for entry in auth.elements],
                                 [('password', 'Admin user'), ('token', 'API user')])
                self.assertEqual(auth.prefill.value, 'password')
                option = form.elements['exclude_adoms']
                self.assertFalse(option.required)
                self.assertEqual(option.parameter_form.prefill.value, expected)
                if version == '2.4':
                    self.assertEqual(namespace['_new_rule_defaults'](), {})
                    self.assertFalse(hasattr(form, 'prefill'))
                    self.assertFalse(hasattr(form, 'default_checked'))
                else:
                    self.assertEqual(form.default_checked, ['exclude_adoms'])
                for saved in ({'user': 'monitoring'}, {'exclude_adoms': []},
                              {'exclude_adoms': ['custom-adom']}):
                    original = copy.deepcopy(saved)
                    self.assertEqual(form.migrate(saved), original)
                    self.assertEqual(saved, original)
                option.parameter_form.prefill.value.clear()
                self.assertEqual(namespace['parameter_form']().elements[
                    'exclude_adoms'].parameter_form.prefill.value, expected)

    def test_split_plugin_registrations(self):
        """
        Verify that all check plugins and the shared parser register exactly once.

        Input:
            Feature modules imported through the Checkmk plugin namespace.

        Output:
            None; assertions fail for missing, duplicate or misplaced registrations.

        """
        expected = {
            'fortimanager_api', 'fortimanager_system', 'fortimanager_license',
            'fortimanager_managed', 'fortimanager_adoms', 'fortimanager_support',
            'fortimanager_resources',
        }
        registrations = [
            (module, plugin)
            for module in CHECK_MODULES
            for name, plugin in vars(module).items()
            if name.startswith('check_plugin_')
        ]
        self.assertCountEqual([plugin.name for _, plugin in registrations], expected)
        for module, plugin in registrations:
            self.assertEqual(plugin.sections, ['fortimanager'])
            self.assertEqual(plugin.check_function.__module__, module.__name__)
            self.assertTrue(callable(plugin.discovery_function))
        sections = [
            section
            for module in CHECK_MODULES
            for name, section in vars(module).items()
            if name.startswith('agent_section_')
        ]
        self.assertEqual([section.name for section in sections], ['fortimanager'])
        self.assertIs(sections[0].parse_function, api_checks.parse_fortimanager)

    def test_precompiled_legacy_imports(self):
        """
        Run imports using the module path retained by previously compiled checks.

        Input:
            A compiled import statement using the historical FortiManager module.

        Output:
            None; assertions verify parser, callback and plugin object identity.

        """
        program = compile(
            'from cmk_addons.plugins.fortimanager.agent_based.fortimanager import '
            'parse_fortimanager, check_api, check_plugin_fortimanager_api, '
            'agent_section_fortimanager',
            '<previously compiled FortiManager check>', 'exec',
        )
        namespace = {}
        exec(program, namespace)
        self.assertIs(namespace['parse_fortimanager'], api_checks.parse_fortimanager)
        self.assertIs(namespace['check_plugin_fortimanager_api'],
                      api_checks.check_plugin_fortimanager_api)
        self.assertIs(namespace['agent_section_fortimanager'], api_checks.agent_section_fortimanager)
        data = namespace['parse_fortimanager']([[json.dumps({'api': {'errors': []}})]])
        self.assertEqual(states(list(namespace['check_api'](data))), [check_types.State.OK])

    def test_legacy_exports_preserve_identity_without_registration_duplicates(self):
        """
        Verify historical exports without exposing duplicate plugin registrations.

        Input:
            Feature modules and the legacy compatibility module.

        Output:
            None; assertions fail for broken exports or duplicate registrations.

        """
        for module in (*CHECK_MODULES, common):
            if module is legacy_checks:
                continue
            for name, value in vars(module).items():
                if name.startswith(('check_plugin_', 'agent_section_')) or (
                    callable(value) and getattr(value, '__module__', '').startswith(
                        'cmk_addons.plugins.fortimanager.'
                    )
                ) or name == 'SYSTEM_FIELDS':
                    with self.subTest(name=name):
                        self.assertIs(getattr(legacy_checks, name), value)
        for name in set(vars(legacy_checks)) | set(dir(legacy_checks)):
            self.assertFalse(name.startswith(('check_plugin_', 'agent_section_')))
        with self.assertRaises(AttributeError):
            getattr(legacy_checks, 'unknown_legacy_attribute')

    def test_manifest_matches_archive_and_agent_executable(self):
        """
        Verify manifest matches archive and agent executable.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        path = builder.build()
        with tarfile.open(path, 'r:gz') as archive:
            metadata = json.load(archive.extractfile('info.json'))
            self.assertEqual(metadata['version'], builder.VERSION)
            self.assertEqual(metadata['version.min_required'], '2.4.0')
            self.assertEqual(metadata['version.usable_until'], '2.5.99')
            self.assertEqual(metadata['name'], 'check_fortimanager')
            self.assertEqual(metadata['title'], 'FortiManager')
            self.assertEqual(metadata['author'], 'Mayuran Asairatnam')
            self.assertEqual(metadata, ast.literal_eval(archive.extractfile('info').read().decode()))
            with tarfile.open(fileobj=io.BytesIO(archive.extractfile('cmk_addons_plugins.tar').read())) as inner:
                self.assertEqual(inner.getnames(), metadata['files']['cmk_addons_plugins'])
                self.assertEqual(metadata['num_files'], len(inner.getnames()))
                expected_modules = {
                    'fortimanager/agent_based/' + Path(module.__file__).name
                    for module in CHECK_MODULES
                } | {'fortimanager/lib/common.py'}
                self.assertTrue(expected_modules.issubset(inner.getnames()))
                self.assertIn('fortimanager/agent_based/fortimanager.py', inner.getnames())
                self.assertEqual(inner.getmember('fortimanager/libexec/agent_fortimanager').mode, 0o755)
                self.assertFalse(any('__pycache__' in name for name in inner.getnames()))
        first = path.read_bytes()
        builder.build()
        self.assertEqual(first, path.read_bytes())


class GraphTests(unittest.TestCase):
    """
    Check graph applicability against the metrics emitted by services.

    AST validation avoids replacing the graph API with a permissive mock.
    Loading in a real Checkmk site still requires an installation check.

    Input:
        Test method selected by the unittest runner.

    Output:
        GraphTests instance.

    """
    def graphs(self, family=FAMILY):
        """
        Read graph registrations directly from their Python syntax tree.

        Input:
            family: Plugin family directory containing graph definitions.

        Output:
            Graph declarations extracted without importing the Checkmk graphing API.

        """
        tree = ast.parse((family / 'graphing' / (family.name + '.py')).read_text())
        graphs = {}
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                continue
            if not isinstance(node.value.func, ast.Name) or node.value.func.id != 'Graph':
                continue
            self.assertTrue(node.targets[0].id.startswith('graph_'))
            args = {kw.arg: kw.value for kw in node.value.keywords}
            name = ast.literal_eval(args['name'])
            self.assertNotIn(name, graphs)
            graphs[name] = {key: set(ast.literal_eval(args[key])) if key in args else set()
                            for key in ('simple_lines', 'compound_lines', 'optional', 'conflicting')}
        return graphs

    def test_graphs_cover_service_metrics_and_partial_resources(self):
        """
        Verify graphs cover service metrics and partial resources.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        graphs = self.graphs()
        metric_tree = ast.parse((FAMILY / 'graphing' / (FAMILY.name + '.py')).read_text())
        metrics = set()
        for node in ast.walk(metric_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Metric':
                metrics.add(next(ast.literal_eval(kw.value) for kw in node.keywords if kw.arg == 'name'))
        # License counts are emitted together. Other measurements need graphs
        # even when a neighbouring resource measurement is missing/invalid.
        cases = [{'used_devices', 'licensed_devices', 'free_devices', 'utilization_percent'}]
        cases += [{name} for name in metrics - {'used_devices', 'licensed_devices', 'free_devices'}]
        cases += [{'devices', 'vdoms'}] if FAMILY.name == 'fortianalyzer' else [{'devices'}]
        for emitted in cases:
            with self.subTest(emitted=emitted):
                applicable = [g for g in graphs.values()
                              if not g['conflicting'] & emitted
                              and (g['simple_lines'] | g['compound_lines']) - g['optional'] <= emitted]
                covered = set().union(*(g['simple_lines'] | g['compound_lines'] for g in applicable))
                self.assertTrue(emitted <= covered, emitted - covered)

    def test_graph_and_metric_definition_names_are_unique(self):
        """
        Verify local names and, when available, FortiAnalyzer names are unique.

        Input:
            Test fixtures and mocks defined by this test case.

        Output:
            None; assertions fail if the expected behavior is not met.

        """
        names = {'Graph': set(), 'Metric': set(), 'Perfometer': set()}
        paths = [FAMILY / 'graphing' / 'fortimanager.py']
        analyzer = (ROOT.parent / 'check_fortianalyzer' / 'cmk_addons_plugins'
                    / 'fortianalyzer' / 'graphing' / 'fortianalyzer.py')
        if analyzer.is_file():
            paths.append(analyzer)
        for path in paths:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in names:
                    name = next(ast.literal_eval(kw.value) for kw in node.keywords if kw.arg == 'name')
                    self.assertNotIn(name, names[node.func.id])
                    names[node.func.id].add(name)


if __name__ == '__main__':
    unittest.main()
