from grafanalib.core import Alert, AlertCondition, Dashboard, Graph, LowerThan, OP_AND, Row, RTYPE_SUM, Target, TimeRange
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
        legendFormat="Average Process CPU Usage in %",
      ),
    ],
  )

GENERAL_PANELS = [number_of_active_processes_graph, avg_cpu_usage_percentage]
