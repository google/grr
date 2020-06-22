from grafanalib.core import Dashboard, Graph, Row, Target
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.reusable_panels import GENERAL_PANELS
from grr_grafanalib_dashboards.config import GRAFANA_DATA_SOURCE

GRR_COMPONENT = "worker"

dashboard = Dashboard(
  title="{}s Dashboard".format(GRR_COMPONENT).title(),
  rows=[
    Row(panels=[panel(GRR_COMPONENT) for panel in row]) 
    for row in GENERAL_PANELS
    ] +
    [
    Row(panels=[
      Graph(
        title="Successful Flows Rate vs. Failed Flows Rate",
        targets=[
          Target(
            expr='sum(rate(flow_completions_total{job="grr_worker"}[10m]))',
            legendFormat="Successes",
          ),
          Target(
            expr='sum(rate(flow_errors_total{job="grr_worker"}[10m]))',
            legendFormat="Failures",
          ),
        ],
      ),
    ]),
    Row(panels=[
      Graph(
        title="Threadpool Latency Rate vs. Queuing Time Rate",
        targets=[
          Target(
            expr='sum(rate(threadpool_working_time_sum{job="grr_worker"}[10m])) / sum(rate(threadpool_working_time_count{job="grr_worker"}[10m]))',
            legendFormat="Latency",
          ),
          Target(
            expr='sum(rate(threadpool_queueing_time_sum{job="grr_worker"}[10m])) / sum(rate(threadpool_queueing_time_count{job="grr_worker"}[10m]))',
            legendFormat="Queueing Time",
          ),
        ],
      ),
      Graph(
        title="Rate of Flow States a GRR Worker has moved through",
        targets=[
          Target(
            expr='rate(grr_worker_states_run_total{job="grr_worker"}[10m])',
            legendFormat="Rate of Fow States moved through",
          ),
        ],
      ),
    ]),
  ],
).auto_panel_ids()

dashboard = add_data_source(dashboard, GRAFANA_DATA_SOURCE)
