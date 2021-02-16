import {Type} from '@angular/core';
import {CollectBrowserHistoryDetails} from '@app/components/flow_details/plugins/collect_browser_history_details';
import {CollectMultipleFilesDetails} from '@app/components/flow_details/plugins/collect_multiple_files_details';
import {CollectSingleFileDetails} from '@app/components/flow_details/plugins/collect_single_file_details';
import {ArtifactCollectorFlowDetails} from './plugins/artifact_collector_flow_details';

import {DefaultDetails} from './plugins/default_details';
import {ListProcessesDetails} from './plugins/list_processes_details';
import {MultiGetFileDetails} from './plugins/multi_get_file_details';
import {OsqueryDetails} from './plugins/osquery_details';
import {Plugin} from './plugins/plugin';
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
  'CollectBrowserHistory': CollectBrowserHistoryDetails,
  'CollectMultipleFiles': CollectMultipleFilesDetails,
  'CollectSingleFile': CollectSingleFileDetails,
  'ListProcesses': ListProcessesDetails,
  'MultiGetFile': MultiGetFileDetails,
  'OsqueryFlow': OsqueryDetails,
  'TimelineFlow': TimelineDetails,
};
