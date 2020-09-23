from grafanalib.core import Alert, AlertCondition, Dashboard, Graph, LowerThan, OP_AND, Row, RTYPE_SUM, Target, TimeRange, YAxes, YAxis, SECONDS_FORMAT, OPS_FORMAT, BYTES_FORMAT
from grr_grafanalib_dashboards import config

def number_of_active_processes_graph(grr_component):
  return Graph(
    title="Number of Active Processes",
    targets=[
      Target(
        expr='sum(up{{job="grr_{}"}})'.format(grr_component),
        legendFormat="Active Processes",
      ),
    ],
    alert=Alert(
      name="Number of Active Processes alert",
      message="The number of active {} processes is below {}".format(grr_component.capitalize(), config.ACTIVE_PROCESSES_ALERTING_CONDITION),
      alertConditions=[
        AlertCondition(
          Target(
            expr='sum(up{{job="grr_{}"}})'.format(grr_component),
            legendFormat="Active Processes",
          ),
          timeRange=TimeRange("10s", "now"),
          evaluator=LowerThan(config.ACTIVE_PROCESSES_ALERTING_CONDITION),
          operator=OP_AND,
          reducerType=RTYPE_SUM
        )
      ],
    )
  )

def avg_cpu_usage_percentage(grr_component):
  return Graph(
    title="CPU Usage",
    targets=[
      Target(
        expr='avg(rate(process_cpu_seconds_total{{job="grr_{}"}}[30s])) * 100'.format(grr_component),
        legendFormat="Average Process CPU Usage",
      ),
    ],
    yAxes=YAxes(
      left=YAxis(max=105, format="percent")
    ),
  )

def sum_process_memory_bytes(grr_component):
  return Graph(
    title="Sum of Process Memory Bytes (across all instances)",
    targets=[
      Target(
        expr='sum(process_resident_memory_bytes{{job="grr_{}"}})'.format(grr_component),
        legendFormat="Resident Memory",
      ),
    ],
    yAxes=YAxes(
      left=YAxis(format=BYTES_FORMAT)
    ),
  )

def db_operations_latency(grr_component):
  return Graph(
    title="Database Operations Latency by Call",
    targets=[
      Target(
        expr='sum by (call) (rate(db_request_latency_sum{{job="grr_{0}"}}[10m]) / rate(db_request_latency_count{{job="grr_{0}"}}[10m]))'.format(grr_component),
        legendFormat="{{call}}",
      ),
    ],
    yAxes=YAxes(
      left=YAxis(format=SECONDS_FORMAT)
    ),  
  )

def db_operations_errors(grr_component):
  return Graph(
    title="Database Operations Errors Rate by Call",
    targets=[
      Target(
        expr='sum by (call) (rate(db_request_errors_total{{job="grr_{0}"}}[10m]))'.format(grr_component),
        legendFormat="{{call}}",
      ),
    ],
    yAxes=YAxes(
      left=YAxis(format=OPS_FORMAT)
    )
  )

def threadpool_outstanding_tasks_vs_threads_num(grr_component):
  return Graph(
    title="Outstanding Tasks vs. Number of Threads",
    targets=[
      Target(
        expr='sum(threadpool_outstanding_tasks{{job="grr_{}"}})'.format(grr_component),
        legendFormat="Outstanding Tasks",
      ),
      Target(
        expr='sum(threadpool_threads{{job="grr_{}"}})'.format(grr_component),
        legendFormat="Threads",
      ),
    ])

def threadpool_cpu_usage(grr_component):
  return Graph(
    title="Threadpool Average CPU Usage",
    targets=[
      Target(
        expr='avg(rate(threadpool_cpu_use{{job="grr_{}"}}[30s])) * 100'.format(grr_component),
        legendFormat="Average Process CPU Usage in % (over all jobs & pools)",
      ),
    ],
    yAxes=YAxes(
      left=YAxis(max=105, format="percent")
    ),
  )

# Each sublist will be parsed as a row in the dashboard.
# Don't add more than 4 panels per row.
GENERAL_PANELS = [
  [
    number_of_active_processes_graph,
    avg_cpu_usage_percentage,
    sum_process_memory_bytes,
  ],
  [
    threadpool_outstanding_tasks_vs_threads_num,
    threadpool_cpu_usage,
    db_operations_errors,
    db_operations_latency,
  ],
]
