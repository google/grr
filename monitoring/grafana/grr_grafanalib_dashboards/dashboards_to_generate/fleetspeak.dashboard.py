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
            legendFormat="{{operation}}",
          ),
        ]
      ),
      Graph(
        title="Successful Datastore Operations Rate per Operation",
        targets=[
          Target(
            expr='sum by (operation) (rate(fleetspeak_server_datastore_operations_completed_latency_count{errored="false"}[10m]))',
            legendFormat="{{operation}}",
          ),
        ]
      ),
      ]
    ),
    Row(panels=[
      Graph(
        title="Client Polls Rate per Type",
        targets=[
          Target(
            expr='sum by (poll_type) (rate(fleetspeak_server_client_polls_total[10m]))',
            legendFormat="{{poll_type}}",
          ),
        ]
      ),
      Graph(
        title="Client Polls Errors Rate per Status",
        targets=[
          Target(
            expr='sum by (http_status_code) (rate(fleetspeak_server_client_polls_total{http_status_code="^(4|5).*"}[10m]))',
            legendFormat="{{http_status_code}}",
          ),
        ]
      ),
      Graph(
        title="Client Poll Latency",
        targets=[
          Target(
            expr='sum(rate(fleetspeak_server_client_polls_operation_time_latency_sum[10m])) / sum(rate(fleetspeak_server_client_polls_operation_time_latency_count[10m]))',
            legendFormat="Operation Time",
          ),
          Target(
            expr='sum(rate(fleetspeak_server_client_polls_read_time_latency_sum[10m])) / sum(rate(fleetspeak_server_client_polls_read_time_latency_count[10m]))',
            legendFormat="Read Time",
          ),
          Target(
            expr='sum(rate(fleetspeak_server_client_polls_write_time_latency_sum[10m])) / sum(rate(fleetspeak_server_client_polls_write_time_latency_count[10m]))',
            legendFormat="Write Time",
          ),
        ]
      ),
      Graph(
        title="Client Polls Rate per Cache",
        targets=[
          Target(
            expr='sum by (cache_hit) (rate(fleetspeak_server_client_polls_total[10m]))',
            legendFormat="Hit: {{cache_hit}}",
          ),
        ]
      ),
      ]
    ),
    Row(panels=[
      Graph(
        title="Messages Ingested per Destination Service",
        targets=[
          Target(
            expr='sum by (destination_service) (rate(fleetspeak_messages_ingested_total[10m]))',
            legendFormat="{{destination_service}}",
          ),
        ]
      ),
      Graph(
        title="Average Message Processing Latency per Service",
        targets=[
          Target(
            expr='sum by (service) (rate(fleetspeak_server_messages_processed_latency_sum[10m])) / sum by (service) (rate(fleetspeak_server_messages_processed_latency_count[10m]))',
            legendFormat="{{service}}",
          ),
        ]
      ),
      Graph(
        title="Payload Bytes Saved per Service",
        targets=[
          Target(
            expr='sum by (service) (rate(fleetspeak_messages_saved_payload_bytes_size[10m]))',
            legendFormat="{{service}}",
          ),
        ]
      ),
      Graph(
        title="Payload Bytes Ingested per Destination Service",
        targets=[
          Target(
            expr='sum by (destination_service) (rate(fleetspeak_messages_ingested_payload_bytes_size[10m]))',
            legendFormat="{{destination_service}}",
          ),
        ]
      ),
      ]
    )
  ]
).auto_panel_ids()

dashboard = add_data_source(dashboard, "fleetspeak")