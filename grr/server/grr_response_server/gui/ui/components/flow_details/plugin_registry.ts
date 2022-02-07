import {Type} from '@angular/core';

import {CollectBrowserHistoryDetails} from '../../components/flow_details/plugins/collect_browser_history_details';
import {CollectFilesByKnownPathDetails} from '../../components/flow_details/plugins/collect_files_by_known_path_details';
import {CollectMultipleFilesDetails} from '../../components/flow_details/plugins/collect_multiple_files_details';
import {CollectSingleFileDetails} from '../../components/flow_details/plugins/collect_single_file_details';

import {ArtifactCollectorFlowDetails} from './plugins/artifact_collector_flow_details';
import {DefaultDetails} from './plugins/default_details';
import {ExecutePythonHackDetails} from './plugins/execute_python_hack_details';
import {FileFinderDetails} from './plugins/file_finder_details';
import {LaunchBinaryDetails} from './plugins/launch_binary_details';
import {ListDirectoryDetails} from './plugins/list_directory_details';
import {ListProcessesDetails} from './plugins/list_processes_details';
import {MultiGetFileDetails} from './plugins/multi_get_file_details';
import {NetstatDetails} from './plugins/netstat_details';
import {OsqueryDetails} from './plugins/osquery_details';
import {Plugin} from './plugins/plugin';
import {ReadLowLevelDetails} from './plugins/read_low_level_details';
import {TimelineDetails} from './plugins/timeline_details';

/**
 * Default details plugin to be used when no appropriate plugin is found.
 */
export const FLOW_DETAILS_DEFAULT_PLUGIN = DefaultDetails;

/**
 * Registry of details plugins: plugin class by flow name.
 */
export const FLOW_DETAILS_PLUGIN_REGISTRY: {[key: string]: Type<Plugin>} = {
  'ArtifactCollectorFlow': ArtifactCollectorFlowDetails,
  'ClientFileFinder': FileFinderDetails,
  'CollectBrowserHistory': CollectBrowserHistoryDetails,
  'CollectFilesByKnownPath': CollectFilesByKnownPathDetails,
  'CollectMultipleFiles': CollectMultipleFilesDetails,
  'CollectSingleFile': CollectSingleFileDetails,
  'ExecutePythonHack': ExecutePythonHackDetails,
  'FileFinder': FileFinderDetails,
  'LaunchBinary': LaunchBinaryDetails,
  'ListDirectory': ListDirectoryDetails,
  'ListProcesses': ListProcessesDetails,
  'MultiGetFile': MultiGetFileDetails,
  'Netstat': NetstatDetails,
  'OsqueryFlow': OsqueryDetails,
  'ReadLowLevel': ReadLowLevelDetails,
  'RecursiveListDirectory': ListDirectoryDetails,
  'TimelineFlow': TimelineDetails,
};
