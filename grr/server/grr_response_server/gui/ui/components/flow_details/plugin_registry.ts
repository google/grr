import {Type} from '@angular/core';

import {CollectBrowserHistoryDetails} from '../../components/flow_details/plugins/collect_browser_history_details';
import {CollectFilesByKnownPathDetails} from '../../components/flow_details/plugins/collect_files_by_known_path_details';
import {CollectMultipleFilesDetails} from '../../components/flow_details/plugins/collect_multiple_files_details';
import {FlowType} from '../../lib/models/flow';

import {ArtifactCollectorFlowDetails} from './plugins/artifact_collector_flow_details';
import {DefaultDetails} from './plugins/default_details';
import {DumpProcessMemoryDetails} from './plugins/dump_process_memory_details';
import {ExecutePythonHackDetails} from './plugins/execute_python_hack_details';
import {FileFinderDetails} from './plugins/file_finder_details';
import {InterrogateDetails} from './plugins/interrogate_details';
import {LaunchBinaryDetails} from './plugins/launch_binary_details';
import {ListDirectoryDetails} from './plugins/list_directory_details';
import {MultiGetFileDetails} from './plugins/multi_get_file_details';
import {NetstatDetails} from './plugins/netstat_details';
import {OnlineNotificationDetails} from './plugins/online_notification_details';
import {OsqueryDetails} from './plugins/osquery_details';
import {Plugin} from './plugins/plugin';
import {ReadLowLevelDetails} from './plugins/read_low_level_details';
import {YaraProcessScanDetails} from './plugins/yara_process_scan_details';

/**
 * Default details plugin to be used when no appropriate plugin is found.
 */
export const FLOW_DETAILS_DEFAULT_PLUGIN = DefaultDetails;

/**
 * Registry of details plugins: plugin class by flow name.
 */
export const FLOW_DETAILS_PLUGIN_REGISTRY:
    {[key in FlowType]?: Type<Plugin>} = {
      [FlowType.ARTIFACT_COLLECTOR_FLOW]: ArtifactCollectorFlowDetails,
      [FlowType.CLIENT_FILE_FINDER]: FileFinderDetails,
      [FlowType.COLLECT_BROWSER_HISTORY]: CollectBrowserHistoryDetails,
      [FlowType.COLLECT_FILES_BY_KNOWN_PATH]: CollectFilesByKnownPathDetails,
      [FlowType.COLLECT_MULTIPLE_FILES]: CollectMultipleFilesDetails,
      [FlowType.DUMP_PROCESS_MEMORY]: DumpProcessMemoryDetails,
      [FlowType.EXECUTE_PYTHON_HACK]: ExecutePythonHackDetails,
      [FlowType.FILE_FINDER]: FileFinderDetails,
      [FlowType.INTERROGATE]: InterrogateDetails,
      [FlowType.LAUNCH_BINARY]: LaunchBinaryDetails,
      [FlowType.LIST_DIRECTORY]: ListDirectoryDetails,
      [FlowType.MULTI_GET_FILE]: MultiGetFileDetails,
      [FlowType.NETSTAT]: NetstatDetails,
      [FlowType.ONLINE_NOTIFICATION]: OnlineNotificationDetails,
      [FlowType.OS_QUERY_FLOW]: OsqueryDetails,
      [FlowType.READ_LOW_LEVEL]: ReadLowLevelDetails,
      [FlowType.RECURSIVE_LIST_DIRECTORY]: ListDirectoryDetails,
      [FlowType.YARA_PROCESS_SCAN]: YaraProcessScanDetails,
    };
