from grafanalib.core import Dashboard, Graph, Row, Target, YAxes, YAxis, SECONDS_FORMAT, OPS_FORMAT
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
        title="API Method Latency Rate by Method",
        targets=[
          Target(
            expr='sum by (method_name) (rate(api_method_latency_sum[10m]) / rate(api_method_latency_count[10m]))',
            legendFormat="{{method_name}}",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=SECONDS_FORMAT)
        ),
      ),
      Graph(
        title="API Calls Count Rate with Status SUCCESS",
        targets=[
          Target(
            expr='sum(rate(api_method_latency_count{status="SUCCESS"}[10m]))',
            legendFormat="Successful Calls Rate",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=OPS_FORMAT)
        ),
      ),
      Graph(
        title="API Calls Count Rate with other statuses (not SUCCESS) by Method",
        targets=[
          Target(
            expr='sum by (method_name) (rate(api_method_latency_count{status!="SUCCESS"}[10m]))',
            legendFormat="{{method_name}}",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=OPS_FORMAT)
        ),
      ),
      Graph(
        title="API Access Probe Latency by Method",
        targets=[
          Target(
            expr='sum by (method_name) (rate(api_access_probe_latency_sum[10m]) / rate(api_access_probe_latency_count[10m]))',
            legendFormat="{{method_name}}",
          ),
        ],
        yAxes=YAxes(
          left=YAxis(format=SECONDS_FORMAT)
        ),
      ),
    ]),
  ],
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
