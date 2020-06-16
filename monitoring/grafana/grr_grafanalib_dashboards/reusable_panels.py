from grafanalib.core import (
    Alert, AlertCondition, Dashboard, Graph,
    LowerThan, OP_AND, Row, RTYPE_SUM,
    Target, TimeRange
)
from grr_grafanalib_dashboards import config

def number_of_active_processes_graph(grr_component):
    return Graph(
        title="Number of Active Processes",
        targets=[
            Target(
                expr='sum(up{{job="grr_{}"}})'.format(grr_component),
                legendFormat="Active Processes",
            ),
        ],
        alert=Alert(
            name="Number of Active Processes alert",
            message="The number of active {} processes is below {}".format(grr_component.capitalize(), config.ACTIVE_PROCESSES_CONDITION),
            alertConditions=[
                AlertCondition(
                    Target(
                        expr='sum(up{{job="grr_{}"}})'.format(grr_component),
                        legendFormat="Active Processes",
                    ),
                    timeRange=TimeRange("10s", "now"),
                    evaluator=LowerThan(config.ACTIVE_PROCESSES_CONDITION),
                    operator=OP_AND,
                    reducerType=RTYPE_SUM
                )
            ],
        )
        )

def avg_cpu_usage_percentage(grr_component):
    return Graph(
        title="Average CPU Usage",
        targets=[
            Target(
                expr='avg(rate(process_cpu_seconds_total{{job="grr_{}"}}[30s])) * 100'.format(grr_component),
                legendFormat="Average Process CPU Usage in %",
            ),
        ],
        )

def sum_process_memory_bytes(grr_component):
    return Graph(
        title="Sum of Process Memory Bytes (across all instances)",
        targets=[
            Target(
                expr='sum(process_resident_memory_bytes{{job="grr_{}"}})'.format(grr_component),
                legendFormat="Resident Memory",
            ),
        ],
        )

def db_request_latency(grr_component):
    return Graph(
        title="Database Request Latency",
        targets=[
            Target(
                expr='rate(db_request_latency_sum{{job="grr_{0}"}}[5m]) / rate(db_request_latency_count{{job="grr_{0}"}}[5m])'.format(grr_component),
                legendFormat="Latency - Call: {{call}}",
            ),
        ],
        )
