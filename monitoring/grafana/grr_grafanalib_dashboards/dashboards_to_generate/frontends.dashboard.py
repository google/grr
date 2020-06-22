from grafanalib.core import Dashboard, Graph, Row, Target
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
      ),
      Graph(
        title="Request Latency Rate",
        targets=[
          Target(
            expr='sum(rate(frontend_request_latency_sum[10m])) / sum(rate(frontend_request_latency_count[10m]))',
            legendFormat="Latency",
          ),
        ],
      ),
      Graph(
        title="RSA Operations Rate",
        targets=[
          Target(
            expr='sum(rate(grr_rsa_operations_total[10m]))',
            legendFormat="Operations Rate",
          ),
        ],
      ),
    ]
    ),
    Row(panels=[
      Graph(
        title="Active Tasks Count",
        targets=[
          Target(
            expr='sum(frontend_active_count)',
            legendFormat="Active Tasks",
          ),
        ],
      ),
      Graph(
        title="Well Known Flows Requests Rate",
        targets=[
          Target(
            expr='sum(rate(well_known_flow_requests_total[10m]))',
            legendFormat="Rate of requests",
          ),
        ],
      ),
      Graph(
        title="Client Unknown Errors Rate",
        targets=[
          Target(
            expr='sum(rate(grr_client_unknown_total[10m]))',
            legendFormat="Rate of errors",
          ),
        ],
      ),
      Graph(
        title="Decoding Errors Rate",
        targets=[
          Target(
            expr='sum(rate(grr_decoding_error_total[10m]))',
            legendFormat="Rate of errors",
          ),
        ],
      ),
    ]
    ),
    Row(panels=[
      Graph(
        title="Decryption Errors Rate",
        targets=[
          Target(
            expr='sum(rate(grr_decryption_error_total[10m]))',
            legendFormat="Rate of errors",
          ),
        ],
      ),
      Graph(
        title="Authenticated vs. Unauthenticated Messages Rate",
        targets=[
          Target(
            expr='sum(rate(grr_authenticated_messages_total[10m]))',
            legendFormat="Rate of authenticated messages",
          ),
          Target(
            expr='sum(rate(grr_unauthenticated_messages_total[10m]))',
            legendFormat="Rate of unauthenticated errors",
          ),
        ],
      ),
    ]),
  ]
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
