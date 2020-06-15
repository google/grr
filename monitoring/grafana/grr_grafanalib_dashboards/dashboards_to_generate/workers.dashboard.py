from grafanalib.core import (
    Dashboard, Graph, Row, Target
)
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.config import PANELS

GRR_COMPONENT = "worker"

dashboard = Dashboard(
    title="{}s Dashboard".format(GRR_COMPONENT).title(),
    rows=[
        Row(panels=[
            panel(GRR_COMPONENT) for panel in PANELS
        ]
        ),
        Row(panels=[
          Graph(
            title="Outstanding Tasks vs. Number of Threads",
            targets=[
                Target(
                    expr='sum(threadpool_outstanding_tasks{{job="grr_{}"}})'.format(GRR_COMPONENT),
                    legendFormat="Outstanding Tasks",
                ),
                Target(
                    expr='sum(threadpool_threads{{job="grr_{}"}})'.format(GRR_COMPONENT),
                    legendFormat="Threads",
                ),
            ],
            ),
            Graph(
            title="Successful Flows vs. Failed Flows Rate",
            targets=[
                Target(
                    expr='sum(rate(flow_completions_total{{job="grr_{}"}}[5m]))'.format(GRR_COMPONENT),
                    legendFormat="Successes",
                ),
                Target(
                    expr='sum(rate(flow_errors_total{{job="grr_{}"}}[5m]))'.format(GRR_COMPONENT),
                    legendFormat="Failures",
                ),
            ],
            ),
        ]),
        Row(panels=[
            Graph(
                title="Threadpool Latency vs. Queuing Time Rate",
                targets=[
                    Target(
                        expr='sum(rate(threadpool_working_time_sum{{job="grr_{0}"}}[5m])) / sum(rate(threadpool_working_time_count{{job="grr_{0}"}}[5m]))'.format(GRR_COMPONENT),
                        legendFormat="Latency",
                    ),
                    Target(
                        expr='sum(rate(threadpool_queueing_time_sum{{job="grr_{0}"}}[5m])) / sum(rate(threadpool_queueing_time_count{{job="grr_{0}"}}[5m]))'.format(GRR_COMPONENT),
                        legendFormat="Queueing Time",
                    ),
                ],
            ),
        ]),
    ],
).auto_panel_ids()

dashboard = add_data_source(dashboard)
