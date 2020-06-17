import setuptools

setup_args = dict(
  name="grr-grafanalib-dashboards",
  description="GRR grafanalib Monitoring Dashboards",
  license="Apache License, Version 2.0",
  url="https://github.com/google/grr/tree/master/monitoring/grafana",
  maintainer="GRR Development Team",
  maintainer_email="grr-dev@googlegroups.com",
  packages=setuptools.find_packages(),
  install_requires=[
    # It is mentioned in grafanalib docs that "We'll probably
    # make changes that break backwards compatibility, although
    # we'll try hard not to", so we stick with version 0.5.7.
    "grafanalib==0.5.7",
  ],
)

setuptools.setup(**setup_args)
