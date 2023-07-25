import {Type} from '@angular/core';

import {ArtifactCollectorFlowForm} from '../../components/flow_args_form/artifact_collector_flow_form';
import {CollectBrowserHistoryForm} from '../../components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '../../components/flow_args_form/collect_multiple_files_form';
import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {FlowType} from '../../lib/models/flow';

import {CollectFilesByKnownPathForm} from './collect_files_by_known_path_form';
import {DumpProcessMemoryForm} from './dump_process_memory_form';
import {ExecutePythonHackForm} from './execute_python_hack_form';
import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {LaunchBinaryForm} from './launch_binary_form';
import {ListDirectoryForm} from './list_directory_form';
import {ListNamedPipesForm} from './list_named_pipes_form';
import {ListProcessesForm} from './list_processes_form';
import {NetstatForm} from './netstat_form';
import {OnlineNotificationForm} from './online_notification_form';
import {OsqueryForm} from './osquery_form';
import {ReadLowLevelForm} from './read_low_level_form';
import {TimelineForm} from './timeline_form';
import {YaraProcessScanForm} from './yara_process_scan_form';

/** Mapping from flow name to Component class to configure the Flow. */
// tslint:disable-next-line:no-any Cannot specify a more precise generic type!
export const FORMS: {[key in FlowType]?: Type<FlowArgumentForm<{}, any>>} = {
  [FlowType.ARTIFACT_COLLECTOR_FLOW]: ArtifactCollectorFlowForm,
  [FlowType.COLLECT_BROWSER_HISTORY]: CollectBrowserHistoryForm,
  [FlowType.COLLECT_FILES_BY_KNOWN_PATH]: CollectFilesByKnownPathForm,
  [FlowType.COLLECT_MULTIPLE_FILES]: CollectMultipleFilesForm,
  [FlowType.DUMP_PROCESS_MEMORY]: DumpProcessMemoryForm,
  [FlowType.EXECUTE_PYTHON_HACK]: ExecutePythonHackForm,
  [FlowType.LAUNCH_BINARY]: LaunchBinaryForm,
  [FlowType.LIST_DIRECTORY]: ListDirectoryForm,
  [FlowType.LIST_NAMED_PIPES_FLOW]: ListNamedPipesForm,
  [FlowType.LIST_PROCESSES]: ListProcessesForm,
  [FlowType.NETSTAT]: NetstatForm,
  [FlowType.ONLINE_NOTIFICATION]: OnlineNotificationForm,
  [FlowType.OS_QUERY_FLOW]: OsqueryForm,
  [FlowType.READ_LOW_LEVEL]: ReadLowLevelForm,
  [FlowType.TIMELINE_FLOW]: TimelineForm,
  [FlowType.YARA_PROCESS_SCAN]: YaraProcessScanForm,

  // Show empty form as fallback for flows that typically do not require
  // configuration.
  [FlowType.COLLECT_EFI_HASHES]: FallbackFlowArgsForm,
  [FlowType.COLLECT_RUNKEY_BINARIES]: FallbackFlowArgsForm,
  [FlowType.DUMP_EFI_IMAGE]: FallbackFlowArgsForm,
  [FlowType.DUMP_FLASH_IMAGE]: FallbackFlowArgsForm,
  [FlowType.GET_CLIENT_STATS]: FallbackFlowArgsForm,
  [FlowType.GET_MBR]: FallbackFlowArgsForm,
  [FlowType.INTERROGATE]: FallbackFlowArgsForm,
  [FlowType.LIST_VOLUME_SHADOW_COPIES]: FallbackFlowArgsForm,
};

/** Fallback form for Flows without configured form. */
export const DEFAULT_FORM = FallbackFlowArgsForm;
