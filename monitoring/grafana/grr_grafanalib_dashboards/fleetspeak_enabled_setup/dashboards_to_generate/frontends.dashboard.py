from grafanalib.core import Dashboard, Graph, Row, Target, YAxes, YAxis, SECONDS_FORMAT
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
  ]
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
