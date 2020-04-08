import {Type} from '@angular/core';

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
};
