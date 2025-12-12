import {
  OutputPlugin,
  OutputPluginDescriptor,
  OutputPluginType,
} from '../../models/output_plugin';
import {assertKeyNonNull} from '../../preconditions';
import {
  OutputPluginDescriptor as ApiOutputPlugin,
  ApiOutputPluginDescriptor,
} from '../api_interfaces';

/** Translates an OutputPluginType from a plugin name. */
export function translateOutputPluginType(
  pluginName: string,
): OutputPluginType {
  switch (pluginName) {
    case 'EmailOutputPlugin':
      return OutputPluginType.EMAIL;
    default:
      return OutputPluginType.UNKNOWN;
  }
}

/** Constructs a OutputPluginDescriptors from a ApiOutputPluginDescriptor. */
export function translateOutputPluginDescriptor(
  opd: ApiOutputPluginDescriptor,
): OutputPluginDescriptor {
  assertKeyNonNull(opd, 'name');

  return {
    pluginType: translateOutputPluginType(opd.name ?? ''),
    friendlyName: opd.friendlyName || opd.name,
    description: opd.description ?? '',
  };
}

/** Constructs a OutputPlugin from a ApiOutputPlugin. */
export function translateOutputPlugin(op: ApiOutputPlugin): OutputPlugin {
  return {
    pluginType: translateOutputPluginType(op.pluginName ?? ''),
    args: op.args,
  };
}
