from grafanalib.core import Dashboard, Graph, Row, Target, Template, Templating, YAxes, YAxis
from grr_grafanalib_dashboards.util import add_data_source
from grr_grafanalib_dashboards.config import CLIENT_LOAD_STATS_DATA_SOURCE

client_id_variable = Template(name="ClientID", query="", type="textbox")

dashboard = Dashboard(
    title="Client Load Stats Dashboard",
    templating=Templating([client_id_variable]),
    rows=[
        Row(panels=[
            Graph(
                title="User CPU Usage",
                targets=[
                    Target(
                        target='Mean User CPU Rate',
                    ),
                    Target(
                        target='Max User CPU Rate',
                    ),
                ],
                yAxes=YAxes(left=YAxis(max=105, format="percent")),
            ),
            Graph(
                title="System CPU Usage",
                targets=[
                    Target(
                        target='Mean System CPU Rate',
                    ),
                    Target(
                        target='Max System CPU Rate',
                    ),
                ],
                yAxes=YAxes(left=YAxis(max=105, format="percent")),
            ),
        ]),
        Row(panels=[
            Graph(
                title="Resident Memory",
                targets=[
                    Target(
                        target='Mean Resident Memory MB',
                    ),
                    Target(
                        target='Max Resident Memory MB',
                    ),
                ],
                yAxes=YAxes(left=YAxis(format="decmbytes")),
            ),
        ]),
    ],
).auto_panel_ids()

dashboard = add_data_source(dashboard, CLIENT_LOAD_STATS_DATA_SOURCE)
