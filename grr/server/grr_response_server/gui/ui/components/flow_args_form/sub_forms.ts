import {Type} from '@angular/core';

import {ArtifactCollectorFlowForm} from '../../components/flow_args_form/artifact_collector_flow_form';
import {CollectBrowserHistoryForm} from '../../components/flow_args_form/collect_browser_history_form';
import {CollectMultipleFilesForm} from '../../components/flow_args_form/collect_multiple_files_form';
import {CollectSingleFileForm} from '../../components/flow_args_form/collect_single_file_form';
import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';

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
export const FORMS: {[key: string]: Type<FlowArgumentForm<{}, any>>} = {
  'ArtifactCollectorFlow': ArtifactCollectorFlowForm,
  'CollectBrowserHistory': CollectBrowserHistoryForm,
  'CollectFilesByKnownPath': CollectFilesByKnownPathForm,
  'CollectMultipleFiles': CollectMultipleFilesForm,
  'CollectSingleFile': CollectSingleFileForm,
  'DumpProcessMemory': DumpProcessMemoryForm,
  'ExecutePythonHack': ExecutePythonHackForm,
  'LaunchBinary': LaunchBinaryForm,
  'ListDirectory': ListDirectoryForm,
  'ListNamedPipesFlow': ListNamedPipesForm,
  'ListProcesses': ListProcessesForm,
  'Netstat': NetstatForm,
  'OnlineNotification': OnlineNotificationForm,
  'OsqueryFlow': OsqueryForm,
  'ReadLowLevel': ReadLowLevelForm,
  'TimelineFlow': TimelineForm,
  'YaraProcessScan': YaraProcessScanForm,

  // Show empty form as fallback for flows that typically do not require
  // configuration.
  'CollectEfiHashes': FallbackFlowArgsForm,
  'CollectRunKeyBinaries': FallbackFlowArgsForm,
  'DumpEfiImage': FallbackFlowArgsForm,
  'DumpFlashImage': FallbackFlowArgsForm,
  'GetClientStats': FallbackFlowArgsForm,
  'GetMBR': FallbackFlowArgsForm,
  'Interrogate': FallbackFlowArgsForm,
  'ListVolumeShadowCopies': FallbackFlowArgsForm,
};

/** Fallback form for Flows without configured form. */
export const DEFAULT_FORM = FallbackFlowArgsForm;
