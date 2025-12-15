import {initTestEnvironment} from '../../../testing';
import {
  OutputPlugin,
  OutputPluginDescriptor,
  OutputPluginType,
} from '../../models/output_plugin';
import {
  OutputPluginDescriptor as ApiOutputPlugin,
  ApiOutputPluginDescriptor,
} from '../api_interfaces';
import {
  translateOutputPlugin,
  translateOutputPluginDescriptor,
} from './output_plugin';

initTestEnvironment();

describe('Output plugin translation test', () => {
  describe('translateOutputPlugin', () => {
    it('converts all fields correctly', () => {
      const api: ApiOutputPlugin = {
        pluginName: 'SomePluginName',
        args: {
          'foo': 'bar',
        },
      };
      const result: OutputPlugin = {
        pluginType: OutputPluginType.UNKNOWN,
        args: {
          foo: 'bar',
        },
      };
      expect(translateOutputPlugin(api)).toEqual(result);
    });

    it('converts optional fields correctly', () => {
      const api: ApiOutputPlugin = {};
      const result: OutputPlugin = {
        pluginType: OutputPluginType.UNKNOWN,
        args: undefined,
      };
      expect(translateOutputPlugin(api)).toEqual(result);
    });
  });

  describe('translateOutputPluginDescriptor', () => {
    it('converts all fields correctly', () => {
      const api: ApiOutputPluginDescriptor = {
        name: 'EmailOutputPlugin',
        friendlyName: 'Email Output Plugin',
        description: 'This is a description',
      };
      const result: OutputPluginDescriptor = {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: 'This is a description',
      };
      expect(translateOutputPluginDescriptor(api)).toEqual(result);
    });

    it('converts optional fields correctly', () => {
      const api: ApiOutputPluginDescriptor = {
        name: 'UnknownOutputPlugin',
      };
      const result: OutputPluginDescriptor = {
        pluginType: OutputPluginType.UNKNOWN,
        friendlyName: 'UnknownOutputPlugin',
        description: '',
      };
      expect(translateOutputPluginDescriptor(api)).toEqual(result);
    });
  });
});
