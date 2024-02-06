# Changelog (important and/or breaking changes).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

* Removed support for Chipsec based flows.
* Removed ClientArtifactCollector flow and related client actions.
* Removed indexing endpoints on snapshot `uname` (searching is still possible
  by individual and combination of system name, release and version).
* Removed support for foreman rules using `uname` of an endpoint (this can be
  simulated by using 3 rules for system name, release and version).
* GRR server Debian package is removed when github actions are updated. The
  docker image and docker compose stack (see section "Added") are the
  recommended wait of running GRR in the future.


### Added
* GRR docker image which contains all grr server components and client
  templates. It is available for every new GRR version for download at
  https://github.com/google/grr/pkgs/container/grr
* Docker compose configuration file to run all GRR/Fleetspeak components in
  separate Docker containers.


### API removed

* GetClientLoadStats API method (`/api/clients/<client_id>/load-stats/<metric>`).
  Client load stats collection functionality was removed from GRR, as
  it was rarely used and Fleetspeak already collects basic client stats anyway.
  Instead of fixing/maintaining the GRR client load stats logic, we will
  better to invest into Fleetspeak's client load stats enhancements.
* ApiReportData definition (used by GetReport, `/api/stats/reports/<name>`)
  changed: support for stack, line and pie charts removed. All stack/line/pie
  chart report plugins removed (namely: GRRVersion1ReportPlugin,
  GRRVersion7ReportPlugin, GRRVersion30ReportPlugin, LastActiveReportPlugin,
  OSBreakdown1ReportPlugin, OSBreakdown7ReportPlugin, OSBreakdown14ReportPlugin,
  OSBreakdown30ReportPlugin, OSReleaseBreakdown1ReportPlugin,
  OSReleaseBreakdown7ReportPlugin, OSReleaseBreakdown14ReportPlugin,
  OSReleaseBreakdown30ReportPlugin, SystemFlowsReportPlugin,
  UserFlowsReportPlugin, MostActiveUsersReportPlugin, UserActivityReportPlugin).

### Planned for removal

Note: GRR release 3.4.7.1 is the **last release** containing the following
features:

* **Artifact parsers**. ArtifactCollector flow supports parsing collected files
  and output of executed commands. Its parsers are not properly maintained,
  are often outdated and fragile. We're going to convert selected parsers
  into standalone flows and remove the artifact parsing subsystem:
  the ArtifactCollector will always work as if "apply_parsers" arguments
  attribute is set to False. Afterwards the "apply_parsers" attribute will be
  deprecated completely. We will provide documentation on integrating
  GRR and ArtifactCollector with well-maintained parsing frameworks like
  [Plaso](https://plaso.readthedocs.io/en/latest/index.html).

* **Built-in cron jobs**. Built-in cron jobs are primarily used for periodic
  hunts. We will provide documentation on how to easily replicate the
  current functionality using external scheduling systems (like Linux cron,
  for example).

  If your workflow depends on GRR built in cron jobs and you anticipate problems
  when migrating it to external schedulers, please reach out to us via email
  or GitHub.

* **GRR server Debian package**. We will stop providing the GRR server Debian
  package as the main way of distributing GRR server and client binaries.
  Instead we will make GRR Docker image a preferred way for running GRR in a
  demo or production environment.

If your workflow depends on any of the above, please feel free reach out to
us via [grr-users](https://groups.google.com/forum/#!forum/grr-users) Google
Group or [GitHub](https://github.com/google/grr/issues).

## [3.4.7.1] - 2023-10-23

### Added

* Created a flow for collecting an identifier of the CrowdStrike agent.
* Podman-based zero-setup development environment.
* Added StatMultipleFiles and HashMultipleFiles flows to be used in
  UIv2.

### Changed

* Renamed AdminUI.new_hunt_wizard.default_output_plugin to
  AdminUI.new_hunt_wizard.default_output_plugins (note the "s" in the end).
  The new option accepts a comma-separated list of names.
* Newly interrogated clients now pick up active hunts automatically.
* Hunts workflow is now available in the new UI: creating hunts from a flow,
  duplicating existing hunts, monitoring hunt progress and inspecting results.

### Removed

* Fully removed deprecated use_tsk flag.
* Removed deprecated plugin_args field from OutputPluginDescriptor.
* Removed deprecated flows: FingerprintFile, KeepAlive, FingerprintFile, FindFiles, SendFile, Uninstall,
  UpdateClient, CollectEfiHashes, DumpEfiImage.
* Deprecated GetFile flow in favor of MultiGetFile.
* Made FileFinder an alias to ClientFileFinder, using ClientFileFinder
  by default everywhere. Legacy FileFinder is still available as
  LegacyFileFinder. Fixed several inconsistencies in ClientFileFinder
  client action. Same for RegistryFinder.
* Removed deprecated client actions: EficheckCollectHashes, EficheckDumpImage, Uninstall, SendFile.
* Removed "Checks" functionality.

### API removed

* Deprecated no-op "keep_client_alive" attribute in ApiCreateClientApprovalArgs.
* Deprecated ListClientActionRequests API call (was no-op after Fleetspeak migration).

## [3.4.6.7] - 2023-03-22

### API removed

* Removed the `labels` field from the `Artifact` message. This change has been
  done in anticipation of the removal of the same field from the official spec
  of [Forensic Artifacts](https://artifacts.readthedocs.io/en/latest/).

### Added

* Introduced Server.grr_binaries_readonly configuration option (set to False
  by default). When set to True, binaries and python hacks can't be overriden
  or deleted.
* Added configuration option Monitoring.http_address to specify server address
  of stats server. Default value will remain 127.0.0.1.


### Changed

* Updates elasticsearch output plugin post request to _bulk in the
  elasticsearch api. Adds a terminating \n and content type headers for
  application/json.

## [3.4.3.1] - 2021-05-19

### API added

* Introduced KillFleetspeak, RestartFleetspeakGrrService,
  DeleteFleetspeakPendingMessages, GetFleetspeakPendingMessages,
  GetFleetspeakPendingMessageCount API methods to provide Fleetspeak-specific
  capabilities for Fleetspeak-enabled clients.
* Introduced ListParsedFlowResults and ListFlowApplicableParsers API methods
  for on-demand artifacts parsing.

### Added

* Introduced Hunt.default_client_rate configuration option.

## [3.4.2.4] - 2020-10-15

### API added

* `GetVersion` method was introduced. It returns information about version of
  the GRR server.
* API shell now validates GRR server version and if it discovers that the server
  is newer than the API client, it will fail on startup. One can bypass this
  behaviour by using the `--no-check-version` flag.

### API removed

* ListAff4AttributeDescriptors API method (/api/reflection/aff4/attributes)
  was removed.
* Support for exporting binary data in the BigQuery output plugin has been
  removed.

### API changed

* `GetFileDetails` now raises if called on non-existing paths instead of
  returning a dummy result.
* `GetVfsFilesArchive` now raises if called on non-existing paths instead of
  returning an empty archive.
* All GRR Protocol Buffers messages now have proper package declarations. It
  means that type URLs of all messages now changed. The Python API client is
  able to handle legacy type URLs, but if you use raw API calls, makes sure it
  does not break your workflow.

### Changed

* The server YAML configuration options path_globs_blacklist and
  path_globs_whitelist in get_flow_files_archive of router_params of
  ApiCallRobotRouter have been renamed to exclude_path_globs and
  include_only_path_globs.
* The server YAML configuration option Artifacts.netgroup_user_blacklist has
  been renamed to Artifacts.netgroup_ignore_users.
* The server YAML configuration options labels_whitelist and
  labels_owners_whitelist in router_params of ApiLabelsRestrictedCallRouter
  have been renamed to allow_labels and allow_labels_owners.
* The server YAML configuration option artifacts_whitelist of
  artifact_collector_flow of router_params of ApiCallRobotRouter has been
  renamed to allow_artifacts.
* The `ExecutePythonHack` flow returns a `ExecutePythonHackResponse` message
  rather than raw string object as a response.
* ApiHunt.hunt_type was introduced and should be used instead of
  a now-deprecated ApiHunt.name.
* Variable hunts now have their arguments filled in the ApiHunt.flow_args
  attribute.
* JSON representation of `st_ino`, `st_dev`, `st_nlink`, `st_blocks`,
  `st_blksize`, `st_rdev` fields of `StatEntry` now use strings rather than
  integers. This is a consequence of increasing the supported integer size of
  these values which might be out of bounds for JSON numbers.
* The `st_crtime` field of `StatEntry` has been renamed to `st_btime`.
* ArtifactCollectorFlowArgs, ArtifactFilesDownloaderFlowArgs:
  * use_tsk is replaced with use_raw_filesystem_access
  * use_tsk is kept for compatibility until 2021-04-01
    * please migrate away from use_tsk to use_raw_filesystem_access until then
  * ValueError is raised if both fields are set

## Removed

* WinUserActivityInvestigationArgs:
  * This message is obsolete, removing it.
* ClientArtifactCollectorArgs
  * Removing use_tsk, since it hasn't been used on the client side

## [3.3.0.0] - 2019-05-22

### API changed

* ListFlows no longer includes "args" attributes into the returned flows.
* ListFlowOutputPluginsLogs, ListFlowOutputPluginErrors,
  ListHuntOutputPluginLogs and ListHuntOutputPluginErrors API calls now always
  report batch_index and batch_size as 0 and no longer include PluginDescriptor
  into the reply.

### API removed

* ListHuntCrashes method no longer accepts "filter" argument.
* ListHunts no longer fills "total_count" attribute of ApiListHuntsResult.
* `ApiHunt` no longer has an `expires` field. Instead, `duration` field has
  been added which can be used to calculate expiry date:
  `start_time + duration`. Note that if the hunt hasn't been started, it does
  not have `start_time` and, in consequence, it does not have expiry time as
  well.
* `ApiModifyHuntArgs` no longer has an `expires` field. Instead, `duration`
  field has been added.
* `artifact` field of `ApiUploadArtifactArgs` no longer accepts arbitrary byte
  stream. Instead, only proper strings are accepted. Since this field is ought
  to be the artifact description in the YAML format and YAML is required to be
  UTF-8 encoded, it makes no sense to accept non-unicode objects.

## [3.2.4.6] - 2018-12-20

### API changed

*  Renamed the task_eta field of the ApiClientActionRequest object to
   leased_until.
*  Got rid of ListCronJobFlows and GetCronJobFlow in favor of ListCronJobRuns
   and GetCronJobRun. ListCronJobRuns/GetCronJobRun return ApiCronJobRun protos
   instead of ApiFlow returned by deleted ListCronJobFlows/GetCronJobFlow.
*  Changed CreateCronJob API call to accept newly introduced
   ApiCreateCronJobArgs instead of an ApiCronJob. ApiCreateCronJobArgs only
   allows to create hunt-based cron jobs.

### API removed

*  All ApiFlowRequest responses do not fill the AFF4 specific
   request_state.request field anymore. Similarly, the task_id and payload
   fields in ApiFlowRequest.responses objects is not populated anymore starting
   from this release.
*  Flow log results returned by ApiListFlowLogsHandler do not contain the name
   of the flow the logs are for anymore.
*  The `ListPendingGlobalNotifications` and `DeletePendingGlobalNotification`
   API methods have been deleted, since GRR no longer supports
   global notifications. The corresponding protos
   `ApiListPendingGlobalNotificationsResult` and
   `ApiDeletePendingGlobalNotificationArgs` have been deprecated.

## [3.2.3.2] - 2018-06-28

### API changed

*   GetGrrBinary API method result type has changed. It was changed to return
    ApiGrrBinary object instead of a binary stream. The old behavior is
    preserved in a newly introduced GetGrrBinaryBlob method.

## [3.2.2.0] - 2018-03-12

### API added

*   Introduced ApiHuntLog, ApiHuntError and ApiFlowLog that are used in
    ApiListHuntLogsResult, ApiListHuntErrorsResult and ApiListFlowLogsResult
    respectively instead of jobs_pb2.FlowLog and jobs_pb2.HuntError. New
    structures are partially backwards compatible with the old ones when used
    via JSON (in protobuf format the fields indices is not compatible):
    "log_message", "flow_name" and "backtrace" fields didn't change. "client_id"
    field doesn't have an AFF4 prefix anymore. "urn" field was removed and
    replaced with "flow_id". "timestamp" field was added.
*   Added "cron_job_id" attribute to ApiCronJob.

### API removed

*   Removed default "age" attribute from the legacy HTTP API JSON. Every value
    rendered in legacy API responses will be dictionary of {value: ..., type:
    ...} instead of {value: ..., type: ..., age: ...}.
*   GetClientVersions API call(/api/clients/<client_id>/versions) does not
    include metadata (last ping, last clock, last boot time, last crash time)
    anymore.
