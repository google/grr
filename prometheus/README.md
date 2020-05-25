# Monitoring GRR with Prometheus + Grafana
The .json files present in this folder are sample [Grafana](https://grafana.com/) dashboards. These dashboards have their data streamed from a [Prometheus](https://prometheus.io/) server, which can be installed in order to aggregate metrics from the different components of GRR, such as the Admin UI, Frontends and Workers.

These sample dashboards are very general and crude, but can form a good basis for a monitoring setup for your GRR server.

## How to integrate Prometheus and Grafana with GRR
Neither Prometheus nor Grafana are installed alongside GRR on default. Refer to GRR's [monitoring
docs](https://grr-doc.readthedocs.io/en/latest/maintaining-and-tuning/monitoring.html) for more information on setting up Prometheus to scrape GRR's exposed metrics. Then, [install Grafana](https://grafana.com/docs/grafana/latest/installation/#install-grafana), run it (usually defaults to `http://<host>:3000`), and make sure to [set Prometheus as a data source](https://grafana.com/docs/grafana/latest/features/datasources/prometheus/#prometheus-data-source). Finally, [import the dashboards](https://grafana.com/docs/grafana/latest/reference/export_import/#importing-a-dashboard) into Grafana. Now all dashboards are visible in the Grafana UI.

## How to use the dashboards
The dashboards give a general overview over the main components of the GRR server, which can be utilized by the user to monitor different metrics of each component. Examples for such metrics can be found [in the docs](https://grr-doc.readthedocs.io/en/latest/maintaining-and-tuning/monitoring.html#example-queries), many of which are already in the sample dashboards.

Additional metrics can be used by exploring `http://<host>:<port>/metrics` for each component of GRR server.

## Setting up alerts on Grafana
Alerts on Grafana dashboards allow the users to stay on top of the deployed GRR server at all times. The dashboards contain sample alerts, such as an alert when GRR's Frontends have no active tasks at a given moment. These sample alerts and additional alerting rules can be easily configured by following the [Grafana Alerting docs](https://grafana.com/docs/grafana/latest/alerting/create-alerts/#add-or-edit-an-alert-rule).

The alerts are not plug-and-play, and before the sample alerts can work with your GRR deployment, you will first have to set up a [notification channel](https://grafana.com/docs/grafana/latest/alerting/notifications/#add-a-notification-channel), which will determine where the alerts will be fired. Such notification channels can be email, Google Chat, Slack etc.
