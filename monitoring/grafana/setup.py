import setuptools

# TODO figure out version, entry_points, cmdclas, data
setup_args = dict(
    name="grr-grafanalib-dashboards",
    # version=VERSION.get("Version", "packageversion"),
    description="GRR grafanalib Monitoring Dashboards",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr/tree/master/monitoring/grafana",
    maintainer="GRR Development Team",
    maintainer_email="grr-dev@googlegroups.com",
    # cmdclass={
    #     "sdist": Sdist,
    # },
    packages=setuptools.find_packages(),
    install_requires=[
        "grafanalib==0.5.7",
    ],
    # data=["version.ini"]
    )

setuptools.setup(**setup_args)
