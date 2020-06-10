from grr_grafanalib_dashboards.config import DATA_SOURCE

def add_data_source(dashboard):
    for row in dashboard.rows:
        for panel in row.panels:
            setattr(panel, "dataSource", DATA_SOURCE)
    return dashboard
