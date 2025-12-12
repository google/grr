import {
  OutputPlugin,
  OutputPluginType,
} from '../../../lib/models/output_plugin';

/**
 * Abstract class for output plugins.
 */
export abstract class OutputPluginData<PluginArgs extends object> {
  readonly prettyName: string = '';
  readonly pluginType: OutputPluginType = OutputPluginType.UNKNOWN;

  abstract getPluginArgs(): PluginArgs;

  getPlugin(): OutputPlugin {
    return {
      pluginType: this.pluginType,
      args: this.getPluginArgs(),
    };
  }
}
