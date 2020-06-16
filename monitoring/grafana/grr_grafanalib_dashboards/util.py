from grr_grafanalib_dashboards.config import GRAFANA_DATA_SOURCE

def add_data_source(dashboard):
  for row in dashboard.rows:
    for panel in row.panels:
      setattr(panel, "dataSource", GRAFANA_DATA_SOURCE)
  return dashboard
