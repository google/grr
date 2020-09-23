from grr_grafanalib_dashboards import reusable_panels

# The data source names are specified after Grafana is set up
# and it can be visited at localhost:3000.
# In GRR Monitoring docs, we suggest naming the data sources "grr-server"
# and "grrafana" respectively, but if it's not the case, change it here.
# For reference, take a look at the docs here:
# https://grr-doc.readthedocs.io/en/latest/maintaining-and-tuning/monitoring.html#example-visualization-and-alerting-setup
GRAFANA_DATA_SOURCE = "grr-server"
CLIENT_LOAD_STATS_DATA_SOURCE = "grrafana"

# An alert will be fired if the number of active processes (of any
# GRR server component) is below this number.
# This alert will be triggered once this condition holds for 10 seconds.
ACTIVE_PROCESSES_ALERTING_CONDITION = 1
