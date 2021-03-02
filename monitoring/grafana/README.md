The module `grr-grafanalib-dashboards` contains sample [Grafana dashboards](https://grafana.com/docs/grafana/latest/features/dashboard/dashboards/)
written using [grafanalib](https://github.com/weaveworks/grafanalib),
that will help you get started quickly introducing monitoring capabilities to your GRR server.

Quick Start
-----------
Before generating the dashboards on your own, note that you can find the sample
dashboard in importable JSON format inside the folder
`grr/monitoring/grafana/grr_grafanalib_dashboards/dashboards_for_use`. From
there you can import the sample dashboards without re-generating them to your
Grafana instance. Follow the instructions below if you want to rebuild or
customize the dashboards.

**Please note the following edge case**: the panel "API Calls Count Rate by other statuses (not
  SUCCESS)" inside the AdminUI dashboard will *not* show a spike in the graph
  when there is only one data point present (only a single API call of a given
  method was made), where the status of the call is not SUCCESS.
  This is due to the way Prometheus' function [rate()](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate) works.

First, make sure to activate the virtual environment of your GRR installation (if you use one), and have Grafana and [Prometheus](https://prometheus.io/docs/prometheus/latest/getting_started/#starting-prometheus)
running on your GRR deployment. To run Prometheus and Grafana with GRR, check out the [monitoring section](https://grr-doc.readthedocs.io/en/latest/maintaining-and-tuning/monitoring.html)
of the documentation.
Then, go to the grafana directory using `cd grr/moniroing/grafana`.
Now use `pip install .` to install the grr-grafanalib-module package. This will install `grafanalib` to your environment as well.

You can now visit the given sample dashboards by browsing to `cd grr_grafanalib_dashboards/dashboards_to_generate`.
This folder will contain all the individual dashboards for each GRR server component. In order to generate these dashboards
to a format that is importable by a Grafana instance, run `generate-dashboards <grr_component_name>.dashboard.py`,
for example: `generate-dashboards frontends.dashboard.py`.
After running this command, new files will be created in the folder with the names `<grr_component_name>.json`. This
JSON file can be imported to your Grafana instance by browsing to the [Import](http://localhost:3000/dashboard/import) page,
clicking the button "Upload .json file" and proceeding with the instructions.

Please note that these dashboards are not exhausitve (by design) as your use case might be unique to you and your GRR
deployment's needs. Use these as general guidelines on how to implement your own dashboards from scratch,
or rather extend these dashboards by introducing new metrics, graphs, alerts etc and fitting them to your individual scenario.
