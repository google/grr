import {ApiOutputPluginDescriptor, ApiOutputPluginDescriptorPluginType} from '../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../testing';
import {OutputPluginDescriptor} from '../models/output_plugin';

import {translateOutputPluginDescriptor} from './output_plugin';


initTestEnvironment();

describe('translateOutputPluginDescriptor', () => {
  it('converts all fields correctly', () => {
    const api: ApiOutputPluginDescriptor = {
      name: 'SomePluginName',
      description: 'This is a description',
      argsType: 'SomePluginNameArgs',
      friendlyName: 'SomePluginFriendlyName',
      pluginType: ApiOutputPluginDescriptorPluginType.INSTANT,
    };
    const result: OutputPluginDescriptor = {
      name: 'SomePluginName',
      description: 'This is a description',
      argsType: 'SomePluginNameArgs',
    };
    expect(translateOutputPluginDescriptor(api)).toEqual(result);
  });
});