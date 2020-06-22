from grafanalib.core import Dashboard, Graph, Row, Target
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.reusable_panels import GENERAL_PANELS
from grr_grafanalib_dashboards.config import GRAFANA_DATA_SOURCE

GRR_COMPONENT = "admin_ui"

dashboard = Dashboard(
  title="{}s Dashboard".format(GRR_COMPONENT).title().replace("_", " "),
  rows=[
    Row(panels=[panel(GRR_COMPONENT) for panel in row]) 
    for row in GENERAL_PANELS
    ] +
    [
    Row(panels=[
      Graph(
        title="API Method Latency Rate",
        targets=[
          Target(
            expr='rate(api_method_latency_sum[10m]) / rate(api_method_latency_count[10m])',
            legendFormat="Latency - Method: {{method_name}}",
          ),
        ],
      ),
      Graph(
        title="API Access Probe Latency",
        targets=[
          Target(
            expr='rate(api_access_probe_latency_sum[10m]) / rate(api_access_probe_latency_count[10m])',
            legendFormat="Latency - Method: {{method_name}}",
          ),
        ],
      ),
    ]),
  ],
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
