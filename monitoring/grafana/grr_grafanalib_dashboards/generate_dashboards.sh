#!/bin/sh

# generate-dashboard -o grafanalib_dashboards/frontends_dashboard.json grafanalib_dashboards/frontends_dashboard.py
# generate-dashboard -o grafanalib_dashboards/workers_dashboard.json grafanalib_dashboards/workers_dashboard.py
#export PYTHONPATH="/usr/local/google/home/giladt/Desktop/grafanalib_dashboards:$PYTHONPATH"
for dashboard in grafanalib_dashboards/*_dashboard.py;
do
    generate-dashboard -o ${dashboard%.*}.json $dashboard
done
