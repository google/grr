from grafanalib.core import Alert, AlertCondition, Dashboard, Graph, LowerThan, OP_AND, Row, RTYPE_SUM, Target, TimeRange, YAxes, YAxis
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.config import ACTIVE_PROCESSES_ALERTING_CONDITION

dashboard = Dashboard(
  title="Fleetspeak Servers Dashboard",
  rows=[
    Row(panels=[
      Graph(
        title="Number of Active Processes",
        targets=[
          Target(
            expr='sum(up{job="fleetspeak"})',
            legendFormat="Active Processes",
          ),
        ],
        alert=Alert(
          name="Number of Active Processes alert",
          message="The number of active Fleetspeak Server processes is below {}".format(ACTIVE_PROCESSES_ALERTING_CONDITION),
          alertConditions=[
            AlertCondition(
              Target(
                expr='sum(up{job="fleetspeak"})',
                legendFormat="Active Processes",
              ),
              timeRange=TimeRange("10s", "now"),
              evaluator=LowerThan(ACTIVE_PROCESSES_ALERTING_CONDITION),
              operator=OP_AND,
              reducerType=RTYPE_SUM
            )
          ],
        )
      ),
      Graph(
        title="Sum of Process Memory Bytes (across all instances)",
        targets=[
          Target(
            expr='sum(process_resident_memory_bytes{job="fleetspeak"})',
            legendFormat="Resident Memory",
          ),
        ]
      ),
      Graph(
        title="CPU Usage",
        targets=[
          Target(
            expr='avg(rate(process_cpu_seconds_total{job="fleetspeak"}[30s])) * 100',
            legendFormat="Average Process CPU Usage in %",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(max=105)
        ),
      ),
    ]
    ),
    Row(panels=[
      Graph(
        title="Datastore Latency",
        targets=[
          Target(
            expr='rate(fleetspeak_server_datastore_operations_completed_latency_sum[10m]) / rate(fleetspeak_server_datastore_operations_completed_latency_count[10m])',
            legendFormat="Latency - Operation: {{operation}}",
          ),
        ]
      ),
      Graph(
        title="Datastore Errors Rate per Operation",
        targets=[
          Target(
            expr='sum by (operation) (rate(fleetspeak_server_datastore_operations_completed_latency_count{errored="true"}[10m]))',
            legendFormat="Operations Error Rate - Operation: {{operation}}",
          ),
        ]
      ),
      Graph(
        title="Client Polls Rate per Type",
        targets=[
          Target(
            expr='sum by (poll_type) (rate(fleetspeak_server_client_polls_total[10m]))',
            legendFormat="Poll Type: {{poll_type}}",
          ),
        ]
      ),
      ]
    ),
  ]
).auto_panel_ids()

dashboard = add_data_source(dashboard, "fleetspeak")