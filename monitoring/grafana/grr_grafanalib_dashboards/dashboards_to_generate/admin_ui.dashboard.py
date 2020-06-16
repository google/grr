from grafanalib.core import (
    Dashboard, Graph, Row, Target
)
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.config import PANELS

GRR_COMPONENT = "admin_ui"

dashboard = Dashboard(
    title="{}s Dashboard".format(GRR_COMPONENT).title(),
    rows=[
        Row(panels=[
            panel(GRR_COMPONENT) for panel in PANELS
        ]
        ),
        Row(panels=[
          Graph(
            title="API Method Latency Rate",
            targets=[
                Target(
                    expr='rate(api_method_latency_sum[5m]) / rate(api_method_latency_count[5m])',
                    legendFormat="Latency - Method: {{method_name}}",
                ),
            ],
            ),
            Graph(
            title="API Access Probe Latency",
            targets=[
                Target(
                    expr='rate(api_access_probe_latency_sum[5m]) / rate(api_access_probe_latency_count[5m])',
                    legendFormat="Latency",
                ),
            ],
            ),
        ]),
    ],
).auto_panel_ids()

dashboard = add_data_source(dashboard)
