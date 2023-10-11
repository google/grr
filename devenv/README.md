# GRR Development Environment

## TL;DR

```bash
$ git clone https://github.com/google/grr
$ cd grr
$ devenv/devenv.sh check_deps
$ devenv/devenv.sh start
```

## Overview

The dev environment relies on [podman](https://podman.io) to set up and run a
local GRR deployment. Each GRR component is run in its own container, and all
containers are bundled together in a pod (so that they share a network stack,
isolated from the host). All containers are run rootless, so Podman needs to be
available on the development machine and subuids need to be set up for the
development user. E.g.:

```bash
sudo usermod --add-subuids 500000-565535 --add-subgids 500000-565535 $USER
```

Services, such as the GRR Admin UI and both the GRR and Fleetspeak MySQL DBs,
are exposed to the host via container port forwarding, so that they can be
accessed directly during development.

The dev environment is set up and controlled via subcommands of the `devenv.sh`
tool (see `devenv/devenv.sh --help` for a description of the full functionality
available).

## Environment Breakdown

The dev environment will run a Fleetspeak-enabled GRR deployment, with a single
GRR client. Each component is run in its own container.

### Containers

- MySQL (`resdefs.MYSQL_CTR`): managing both the `grr` and `fleetspeak` DBs
- Fleetspeak Admin (`resdefs.FLEETSPEAK_ADMIN_CTR`)
- Fleetspeak Frontend (`resdefs.FLEETSPEAK_FRONTEND_CTR`)
- GRR AdminUI (`resdefs.GRR_ADMIN_UI_CTR`)
- GRR Worker (`resdefs.GRR_WORKER_CTR`)
- GRR Fleetspeak Frontend (`resdefs.GRR_FRONTEND_CTR`)
- GRR Client (`resdefs.GRR_CLIENT_CTR`): running the fleetspeak client, which
  spawns the GRR client process

### Persistent Data

Data that needs to persist between devenv invocations is mounted inside the
containers as persistent volumes:
- `resdefs.MYSQL_DATA_VOL`: mounted inside the MySQL container (at
  `/var/lib/mysql`), holding both the `grr` and `fleetspeak` DBs;
- `resdefs.GRR_PERSIST_VOL`: mounted insde all GRR containers (at
  `/grr/persist`), holding the GRR Python virtual environment (i.e. build data
  and deps), and the Fleetspeak client state file.

### GRR Source Code

The GRR source code is bind-mounted inside the GRR containers so that code code
changes are immediately available. Note however that, upon code changes, a
container restart is needed so that Python can pick up the changes (i.e
`devenv.sh restart {container}`).

### GRR Configuration

The config used by all GRR containers resides under `devenv/config`. As the
entire GRR source tree is bind-mounted into all the GRR containers, this
directory is also available, at runtime, to all GRR components.

## Development Flow Example

1.  check that the dev environment can run on the host system: `bash
    devenv/devenv.sh check_deps`
2.  start the dev environment: `bash devenv/devenv.sh start`
3.  check that everything is up and running: `bash devenv/devenv.sh status`
4.  find the generated GRR client ID: `bash curl -su admin:admin
    http://localhost:4280/api/clients \ | sed 1d \ | jq -r
    ".items[].value.client_id.value"` Note: the above assumes the default values
    in `devenv/config.py` (such as Admin UI port number and admin user details)
    have not been changed. It also assumes `curl`, `sed`, and `jq` are available
    on the host system.
5.  open a browser and go to the Admin UI client info page:
    `http://localhost:4280/v2/clients/{CLIENT_ID}`
6.  edit the GRR worker python code;
7.  restart the `grr-worker` container so that code changes are picked up:
    `devenv/devenv.sh restart grr-worker`

### Debugging

(still assuming GRR worker)

- add a `breakpoint()` call at the targeted location inside the GRR worker
  python code;
- restart the GRR worker container, attaching to its TTY, and iteract with
  `pdb`: `bash devenv/devenv.sh restart -a grr-worker` Notice the `-a` option
  (attach).

### Meta: Developing the Development Environment

## Resources

The dev environment is built around the concept of resources - everything is a
resource that can be either up (active) or down (inactive). A resource may need
other resources to be active (up) before it itself can be brought up. In other
words, resources take dependencies on other resources. For instance, the MySQL
container will need the MySQL container image to be built before it can start.

Each resource is implemented by extending the abstract base class
`reslib.Resource`. The specific resource then needs to implement:

- `Resource.is_up()`: check whether the resource is up or down;
- `Resource.create()`: bring up / create the resource;
- `Resource.destroy()`: take down / destroy the resource.

If the resource needs to specify dependencies it can do so by passing a list of
those to the base `Resource` constructor (via the `deps` argument).

Additional functionality is provided by the base `Resource` class, such as:

- bringing up a resource by ensuring that all its dependencies are up before
  creating the resource itself (implemented by `Resource.ensure()`);
- destroying the resource if necessary (implemented by `Resource.clean()`);
- destroying a resource and its dependencies (`Resource.deep_clean()`).

Resources are implemented by two modules:

- `reslib.py`: contains resource functionality (e.g. handing Podman data
  volumes, container images, and containers);
- `resdefs.py`: contains the actual resource definitions (i.e. the volumes,
  images, containers, etc, that make up the dev environment).

The dev environment itself is implemented via a `Resource` that depends on all
GRR containers being up, as well as an admin user being set up for the GRR Admin
UI. This way, bringing up the environment is a just a mater of calling this
resource's `ensure()` function.

## Command Line Interface

All dev environment functionality is implemented via subcommands of `devenv.sh`.
`devenv.sh` itself is a wrapper script that runs the `devenv` Python package
in-place (i.e. without the need to py-install it).

Command line parsing is done via the standard Python `argparse` module, in
`cli.py`. Each subcommand is implemented via a function defined in `commands.py`,
and decorated with `cli.subcommand`. This decorator ensures that the function is
register as a subcommand and takes care of parsing its command line. The
subcommand function will receive its parsed arguments in the form of a
`argparse.Namespace` object.

The `cli.subcommand` decorator receives the parsing instructions as arguments.
These are passed through almost verbatim to `argparse` functions (see
`subcommand` code doc for the exact format).
