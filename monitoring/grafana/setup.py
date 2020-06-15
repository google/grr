import setuptools

# TODO figure out version, cmdclas, data
setup_args = dict(
    name="grr-grafanalib-dashboards",
    # version=VERSION.get("Version", "packageversion"),
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
    # cmdclass={
    #     "sdist": Sdist,
    # },
    # data=["version.ini"]
    )

setuptools.setup(**setup_args)
