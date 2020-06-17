from grafanalib.core import (
    Dashboard, Graph, Row, Target
)
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.config import PANELS

GRR_COMPONENT = "frontend"

dashboard = Dashboard(
    title="{}s Dashboard".format(GRR_COMPONENT).title(),
    rows=[
        Row(panels=[
            panel(GRR_COMPONENT) for panel in PANELS
        ]
        ),
        Row(panels=[
          Graph(
            title="QPS",
            targets=[
                Target(
                    expr='sum(rate({}_request_count_total[1m]))'.format(GRR_COMPONENT),
                    legendFormat="Requests",
                ),
            ],
            ),
            Graph(
            title="Request Latency Rate",
            targets=[
                Target(
                    expr='sum(rate({0}_request_latency_sum[5m])) / sum(rate({0}_request_latency_count[5m]))'.format(GRR_COMPONENT),
                    legendFormat="Latency",
                ),
            ],
            ),
        ]),
        Row(panels=[
            Graph(
                title="Active Tasks Count",
                targets=[
                    Target(
                        expr='sum({}_active_count)'.format(GRR_COMPONENT),
                        legendFormat="Active Tasks",
                    ),
                ],
            ),
            Graph(
                title="Well Known Flows Requests",
                targets=[
                    Target(
                        expr='sum(well_known_flow_requests_total)',
                        legendFormat="Total number of requests",
                    ),
                ],
            ),
        ]),
    ],
).auto_panel_ids()

dashboard = add_data_source(dashboard)
