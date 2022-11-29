import {ApiOutputPluginDescriptor} from '../../lib/api/api_interfaces';
import {OutputPluginDescriptor} from '../models/output_plugin';
import {assertKeyNonNull} from '../preconditions';

/** Constructs a OutputPluginDescriptor from a ApiOutputPluginDescriptor. */
export function translateOutputPluginDescriptor(opd: ApiOutputPluginDescriptor):
    OutputPluginDescriptor {
  assertKeyNonNull(opd, 'name');

  return {
    name: opd.name ?? '',
    description: opd.description ?? '',
    argsType: opd.argsType ?? '',
  };
}