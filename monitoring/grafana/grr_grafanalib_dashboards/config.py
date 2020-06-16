from grr_grafanalib_dashboards import reusable_panels

DATA_SOURCE = "grr-server"
ACTIVE_PROCESSES_CONDITION = 1
PANELS = [
    reusable_panels.number_of_active_processes_graph, 
    reusable_panels.avg_cpu_usage_percentage,
    reusable_panels.db_request_latency
    ]
