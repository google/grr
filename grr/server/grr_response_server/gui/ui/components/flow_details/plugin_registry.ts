import {Type} from '@angular/core';
import {CollectBrowserHistoryDetails} from '@app/components/flow_details/plugins/collect_browser_history_details';
import {CollectSingleFileDetails} from '@app/components/flow_details/plugins/collect_single_file_details';

import {DefaultDetails} from './plugins/default_details';
import {MultiGetFileDetails} from './plugins/multi_get_file_details';
import {Plugin} from './plugins/plugin';

/**
 * Default details plugin to be used when no appropriate plugin is found.
 */
export const FLOW_DETAILS_DEFAULT_PLUGIN = DefaultDetails;

/**
 * Registry of details plugins: plugin class by flow name.
 */
export const FLOW_DETAILS_PLUGIN_REGISTRY: {[key: string]: Type<Plugin>} = {
  'MultiGetFile': MultiGetFileDetails,
  'CollectBrowserHistory': CollectBrowserHistoryDetails,
  'CollectSingleFile': CollectSingleFileDetails,
};
