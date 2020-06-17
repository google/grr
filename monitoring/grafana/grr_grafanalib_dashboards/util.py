def add_data_source(dashboard, datasource):
  """Attach a Grafana data source to all panels in a dashboard."""
  for row in dashboard.rows:
    for panel in row.panels:
      setattr(panel, "dataSource", datasource)
  return dashboard
