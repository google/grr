The .json files present in this folder are [Grafana](https://grafana.com/) dashboards. These dashboards have their data streamed from a [Prometheus](https://prometheus.io/) server, which can be installed in order to aggregate metrics from the different components of GRR, such as the Admin UI, Frontends and Workers.

Neither Prometheus nor Grafana are installed alongside GRR on default. Refer to GRR's [monitoring
docs](https://grr-doc.readthedocs.io/en/latest/maintaining-and-tuning/monitoring.html) for more information on setting up Prometheus to scrape GRR's exposed
metrics. Then, [install
Grafana](https://grafana.com/docs/grafana/latest/installation/#install-grafana), make sure to [set Prometheus as a data source](https://grafana.com/docs/grafana/latest/features/datasources/prometheus/#prometheus-data-source) and finally [import the dashboards](https://grafana.com/docs/grafana/latest/reference/export_import/#importing-a-dashboard) into Grafana.
