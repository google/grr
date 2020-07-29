from grafanalib.core import Dashboard, Graph, Row, Target, YAxes, YAxis, SECONDS_FORMAT, OPS_FORMAT
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.reusable_panels import GENERAL_PANELS
from grr_grafanalib_dashboards.config import GRAFANA_DATA_SOURCE

GRR_COMPONENT = "frontend"

dashboard = Dashboard(
  title="{}s Dashboard".format(GRR_COMPONENT).title(),
  rows=[
    Row(panels=[panel(GRR_COMPONENT) for panel in row]) 
    for row in GENERAL_PANELS
    ] +
    [
      Row(panels=[
      Graph(
        title="QPS",
        targets=[
          Target(
            expr='sum(rate(frontend_request_count_total[1m]))',
            legendFormat="Requests",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format="reqps")
        ),
      ),
      Graph(
        title="Request Latency",
        targets=[
          Target(
            expr='sum(rate(frontend_request_latency_sum[10m])) / sum(rate(frontend_request_latency_count[10m]))',
            legendFormat="Latency",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=SECONDS_FORMAT)
        ),
      ),
      Graph(
        title="Well Known Flows Requests Rate by Flow",
        targets=[
          Target(
            expr='sum by (flow) (rate(well_known_flow_requests_total[10m]))',
            legendFormat="{{flow}}",
          ),
        ],
      ),
      Graph(
        title="GRR Client Crashes",
        targets=[
          Target(
            expr='sum(rate(grr_client_crashes_total{job="grr_frontend"}[10m]))',
            legendFormat="Rate of Client crashes",
          ),
        ],
      )
    ]
    ),
    Row(panels=[
      Graph(
        title="RSA Operations Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_rsa_operations_total[10m]))',
            legendFormat="Rate of Operations",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=OPS_FORMAT)
        ),
      ),
      Graph(
        title="GRR Unknown Client Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_client_unknown_total[10m]))',
            legendFormat="Rate of Unknown Clients",
          ),
        ],
      ),
      Graph(
        title="Decoding Errors Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_decoding_error_total[10m]))',
            legendFormat="Rate of Decoding Errors",
          ),
        ],
      ),
      Graph(
        title="Decryption Errors Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_decryption_error_total[10m]))',
            legendFormat="Rate of Decryption Errors",
          ),
        ],
      )
    ]
    ),
    Row(panels=[
      Graph(
        title="Authenticated Messages Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_authenticated_messages_total[10m]))',
            legendFormat="Rate of Authenticated Messages",
          ),
        ],
      ),
      Graph(
        title="Unauthenticated Messages Rate (across all instances)",
        targets=[
          Target(
            expr='sum(rate(grr_unauthenticated_messages_total[10m]))',
            legendFormat="Rate of Unauthenticated Messages",
          ),
        ],
      ),
    ]
    ),
  ]
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
