def add_data_source(dashboard, datasource):
  for row in dashboard.rows:
    for panel in row.panels:
      setattr(panel, "dataSource", datasource)
  return dashboard
