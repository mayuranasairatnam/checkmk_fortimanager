"""
Metric definitions and historical graphs.
"""
from cmk.graphing.v1 import Title
from cmk.graphing.v1.metrics import AutoPrecision, Color, DecimalNotation, IECNotation, Metric, StrictPrecision, Unit
from cmk.graphing.v1.graphs import Graph, MinimalRange
from cmk.graphing.v1.perfometers import Closed, FocusRange, Perfometer

COUNT = Unit(DecimalNotation(''), StrictPrecision(0))
PERCENT = Unit(DecimalNotation('%'), AutoPrecision(1))
BYTES = Unit(IECNotation('B'), AutoPrecision(2))
DAYS = Unit(DecimalNotation('days'), StrictPrecision(0))

metric_used_devices = Metric(name='used_devices', title=Title('Used device licenses'), unit=COUNT, color=Color.BLUE)
metric_licensed_devices = Metric(name='licensed_devices', title=Title('Licensed devices'), unit=COUNT, color=Color.GREEN)
metric_free_devices = Metric(name='free_devices', title=Title('Free device licenses'), unit=COUNT, color=Color.CYAN)
metric_utilization_percent = Metric(name='utilization_percent', title=Title('Device license utilization'), unit=PERCENT, color=Color.PURPLE)
metric_devices = Metric(name='devices', title=Title('ADOM devices'), unit=COUNT, color=Color.BLUE)
metric_fmg_max_adoms = Metric(name='fmg_max_adoms', title=Title('Maximum ADOMs'), unit=COUNT, color=Color.BLUE)
metric_fmg_max_device_groups = Metric(name='fmg_max_device_groups', title=Title('Maximum device groups'), unit=COUNT, color=Color.GREEN)
metric_fmg_fortigates = Metric(name='fmg_fortigates', title=Title('FortiGates'), unit=COUNT, color=Color.BLUE)
metric_fmg_fortiap = Metric(name='fmg_fortiap', title=Title('FortiAPs'), unit=COUNT, color=Color.GREEN)
metric_fmg_fortiswitch = Metric(name='fmg_fortiswitch', title=Title('FortiSwitches'), unit=COUNT, color=Color.CYAN)
metric_fmg_fortiextender = Metric(name='fmg_fortiextender', title=Title('FortiExtenders'), unit=COUNT, color=Color.PURPLE)
metric_fmg_support_days = Metric(name='fmg_support_days', title=Title('Remaining support lifetime'), unit=DAYS, color=Color.ORANGE)
metric_fmg_cpu_percent = Metric(name='fmg_cpu_percent', title=Title('CPU average'), unit=PERCENT, color=Color.BLUE)
metric_fmg_disk_percent = Metric(name='fmg_disk_percent', title=Title('Disk usage'), unit=PERCENT, color=Color.GREEN)
metric_fmg_memory_percent = Metric(name='fmg_memory_percent', title=Title('Memory usage'), unit=PERCENT, color=Color.PURPLE)
metric_fmg_memory_used = Metric(name='fmg_memory_used', title=Title('Memory used'), unit=BYTES, color=Color.BLUE)
metric_fmg_memory_total = Metric(name='fmg_memory_total', title=Title('Memory total'), unit=BYTES, color=Color.GREEN)
metric_fmg_memory_free = Metric(name='fmg_memory_free', title=Title('Memory free'), unit=BYTES, color=Color.CYAN)

graph_fortimanager_license = Graph(name='fortimanager_license', title=Title('FortiManager device licenses'),
    simple_lines=['used_devices', 'licensed_devices', 'free_devices'])
graph_fortimanager_managed = Graph(name='fortimanager_managed', title=Title('FortiManager managed devices'),
    simple_lines=['fmg_fortigates', 'fmg_fortiap', 'fmg_fortiswitch', 'fmg_fortiextender'],
    optional=['fmg_fortiextender'])
graph_fortimanager_resources = Graph(name='fortimanager_resources', title=Title('FortiManager utilization'),
    simple_lines=['fmg_cpu_percent', 'fmg_memory_percent', 'fmg_disk_percent'])
graph_fortimanager_memory = Graph(name='fortimanager_memory', title=Title('FortiManager memory'),
    simple_lines=['fmg_memory_used', 'fmg_memory_total', 'fmg_memory_free'])
perfometer_fortimanager_license = Perfometer(name='fortimanager_license',
    focus_range=FocusRange(Closed(0), Closed(100)), segments=['utilization_percent'])

# Single-metric graphs also work when other API measurements are unavailable.
graph_fortimanager_license_utilization = Graph(name='fortimanager_license_utilization', title=Title('FortiManager Device license utilization'),
    simple_lines=['utilization_percent'], minimal_range=MinimalRange(0, 100))
graph_fortimanager_max_adoms = Graph(name='fortimanager_max_adoms', title=Title('FortiManager Maximum ADOMs'),
    simple_lines=['fmg_max_adoms'])
graph_fortimanager_max_device_groups = Graph(name='fortimanager_max_device_groups', title=Title('FortiManager Maximum device groups'),
    simple_lines=['fmg_max_device_groups'])
graph_fortimanager_adom_devices = Graph(name='fortimanager_adom_devices', title=Title('FortiManager ADOM devices'),
    simple_lines=['devices'], conflicting=['vdoms'])
graph_fortimanager_fortigates = Graph(name='fortimanager_fortigates', title=Title('FortiManager FortiGates'),
    simple_lines=['fmg_fortigates'])
graph_fortimanager_fortiap = Graph(name='fortimanager_fortiap', title=Title('FortiManager FortiAPs'),
    simple_lines=['fmg_fortiap'])
graph_fortimanager_fortiswitch = Graph(name='fortimanager_fortiswitch', title=Title('FortiManager FortiSwitches'),
    simple_lines=['fmg_fortiswitch'])
graph_fortimanager_fortiextender = Graph(name='fortimanager_fortiextender', title=Title('FortiManager FortiExtenders'),
    simple_lines=['fmg_fortiextender'])
graph_fortimanager_support = Graph(name='fortimanager_support', title=Title('FortiManager Remaining support lifetime'),
    simple_lines=['fmg_support_days'])
graph_fortimanager_cpu = Graph(name='fortimanager_cpu', title=Title('FortiManager CPU average'),
    simple_lines=['fmg_cpu_percent'], minimal_range=MinimalRange(0, 100))
graph_fortimanager_disk = Graph(name='fortimanager_disk', title=Title('FortiManager Disk usage'),
    simple_lines=['fmg_disk_percent'], minimal_range=MinimalRange(0, 100))
graph_fortimanager_memory_percent = Graph(name='fortimanager_memory_percent', title=Title('FortiManager Memory usage'),
    simple_lines=['fmg_memory_percent'], minimal_range=MinimalRange(0, 100))
graph_fortimanager_memory_used = Graph(name='fortimanager_memory_used', title=Title('FortiManager Memory used'),
    simple_lines=['fmg_memory_used'])
graph_fortimanager_memory_total = Graph(name='fortimanager_memory_total', title=Title('FortiManager Memory total'),
    simple_lines=['fmg_memory_total'])
graph_fortimanager_memory_free = Graph(name='fortimanager_memory_free', title=Title('FortiManager Memory free'),
    simple_lines=['fmg_memory_free'])
