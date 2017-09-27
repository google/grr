# GRR API client library

GRR API client library provides an easy way to talk to GRR AdminUI server to
fetch data or trigger actions. It can be used for GRR scripting and automation.

## Installation

To install the latest release version from PIP:

```
pip install grr-api-client
```

To install the latest dev version from source:

```
sudo apt-get install -y \
  protobuf-compiler \
  python-dev \
  python-pip

sudo pip install --upgrade pip
sudo pip install virtualenv

git clone https://github.com/google/grr.git
virtualenv GRR_NEW
source GRR_NEW/bin/activate

cd grr/api_client/python
pip install --editable .
```

## Initializing the GRR API object

```
from grr_api_client import api
grrapi = api.InitHttp(api_endpoint="http://localhost:1234",
                      auth=("user", "pwd"))
```

This creates a root GRR API object that will connect to the
"http://localhost:1234" HTTP API endpoint. This URL should be the same with
GRR's AdminUI URL.

GRR API library uses [requests](http://docs.python-requests.org/en/master/)
library under the hood. The *auth* argument is passed verbatim to the *requests*
library. In the example above the `("user", "pwd")` value will force the
requests library to do HTTP Basic authentication with user name "user" and
password "pwd".

In case your GRR AdminUI server is configured to use any other authentication
scheme, any authentication method [supported by requests
library](http://docs.python-requests.org/en/master/user/authentication/) can be
used (or [custom one can be
implemented](http://docs.python-requests.org/en/master/user/advanced/#custom-authentication)).

## Example: Collect client IDs for a given hostname

```
from grr_api_client import api
grrapi = api.InitHttp(api_endpoint="http://localhost:1234",
                      auth=("user", "pwd"))

search_result = grrapi.SearchClients("host:suspicious.corp.com")
result = {}
for client in search_result:
  client_id = client.client_id
  client_last_seen_at = client.data.last_seen_at
  result[client_id] = client_last_seen_at
print result
```

## Example: add *"suspicious"* label to all clients with a given hostname

```
from grr_api_client import api
grrapi = api.InitHttp(api_endpoint="http://localhost:1234",
                      auth=("user", "pwd"))

search_result = grrapi.SearchClients("host:suspicious.corp.com")
for client in search_result:
  client.AddLabels(["suspicious"])
```

## Example: start a FileFinder hunt

*flow_args* and *hunt_runner_args* below are protobufs (see Protobuf library
[docs](https://developers.google.com/protocol-buffers/docs/pythontutorial)). See
definitions of
[FileFinderArgs](https://github.com/google/grr/blob/7cdf490f9be2ccc0a8160c9b8ae23b73922049d5/grr/proto/flows.proto#L1626),
[HuntRunnerArgs](https://github.com/google/grr/blob/7cdf490f9be2ccc0a8160c9b8ae23b73922049d5/grr/proto/flows.proto#L286),
[ForemanClientRuleSet](https://github.com/google/grr/blob/a103753a065f14f77b0df841e224777797f870d8/grr/proto/jobs.proto#L1471).

```
from grr_api_client import api
grrapi = api.InitHttp(api_endpoint="http://localhost:1234",
                      auth=("user", "pwd"))

# Initialize args protobuf for a FileFinder flow: FileFinderArgs.
flow_args = grrapi.types.CreateFlowArgs("FileFinder")
# FileFinderArgs.paths gets initialized with an example value,
# we should get rid of it.
flow_args.ClearField("paths")
flow_args.paths.append("/var/log/*")
flow_args.action.action_type = flow_args.action.DOWNLOAD

# Initialize hunt runner args.
hunt_runner_args = grrapi.types.CreateHuntRunnerArgs()
rule = hunt_runner_args.client_rule_set.rules.add()
rule.rule_type = rule.LABEL
rule.label.label_names.append("suspicious")

# Create a hunt and start it.
hunt = grrapi.CreateHunt(flow_name="FileFinder", flow_args=flow_args,
                         hunt_runner_args=hunt_runner_args)
hunt = hunt.Start()
```

## Using command line API shell

*grr_api_shell* command provides an IPython shell with a preinitialized *grrapi*
object (it's installed as part of grr-api-client PIP package).

```
usage: grr_api_shell [-h] [--page_size PAGE_SIZE]
                     [--basic_auth_username BASIC_AUTH_USERNAME]
                     [--basic_auth_password BASIC_AUTH_PASSWORD] [--debug]
                     [--exec_code EXEC_CODE] [--exec_file EXEC_FILE]
                     api_endpoint

positional arguments:
  api_endpoint          API endpoint specified as host[:port]

optional arguments:
  -h, --help            show this help message and exit
  --page_size PAGE_SIZE
                        Page size used when paging through collections of
                        items.
  --basic_auth_username BASIC_AUTH_USERNAME
                        HTTP basic auth username (HTTP basic auth will be used
                        if this flag is set.
  --basic_auth_password BASIC_AUTH_PASSWORD
                        HTTP basic auth password (will be used if
                        basic_auth_username is set.
  --debug               Enable debug logging.
  --exec_code EXEC_CODE
                        If present, no console is started but the code given
                        in the flag is run instead (comparable to the -c
                        option of IPython). The code will be able to use a
                        predefined global 'grrapi' object.
  --exec_file EXEC_FILE
                        If present, no console is started but the code given
                        in command file is supplied as input instead. The code
                        will be able to use a predefined global 'grrapi'
                        object.
```

## API shell command line one-liners

*grr_api_shell* tool can be used for command line one-liners.

Print client IDs of all the clients known to GRR:

```
grr_api_shell --basic_auth_username "user" --basic_auth_password "pwd" \
  --exec_code 'print "\n".join(c.client_id for c in grrapi.SearchClients(""))' \
  http://localhost:1234
```

Write all the files downloaded by a specific flow into the "flow_results.zip"
file:

```
grr_api_shell --basic_auth_username "user" --basic_auth_password "pwd" \
  --exec_code 'grrapi.Client("C.1234567890ABCDEF").Flow("F:BB628B23").GetFilesArchive().WriteToFile("./flow_results.zip")' \
  http://localhost:1234
```

Download an archive of files collected from a GRR client that are stored in
*/fs/os/var/log/* VFS folder:

```
grr_api_shell --basic_auth_username "user" --basic_auth_password "pwd" \
  --exec_code 'grrapi.Client("C.1234567890ABCDEF").File("/fs/os/var/log").GetFilesArchive().WriteToFile("./all_client_files.zip")' \
  http://localhost:1234
```

Download an archive of all files collected from a GRR client:

```
grr_api_shell --basic_auth_username "user" --basic_auth_password "pwd" \
  --exec_code 'grrapi.Client("C.1234567890ABCDEF").File("/fs").GetFilesArchive().WriteToFile("./all_client_files.zip")' \
  http://localhost:1234
```

Print all results of a particular flow in a text-protobuf format:

```
grr_api_shell --basic_auth_username "user" --basic_auth_password "pwd" \
  --exec_code 'for r in grrapi.Client("C.1234567890ABCDEF").Flow("F:BB628B23").ListResults(): print str(r.payload)' \
  http://localhost:1234
```
