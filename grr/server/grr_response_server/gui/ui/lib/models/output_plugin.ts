/**
 * Output plugin type.
 */
export enum OutputPluginType {
  UNKNOWN = 'UnknownOutputPlugin',
  EMAIL = 'EmailOutputPlugin',
}

/** Combine both OutputPlugin and OutputPluginDescriptor from the backend */
export interface OutputPluginDescriptor {
  readonly pluginType: OutputPluginType;
  readonly friendlyName: string;
  readonly description: string;
}

/** OutputPluginDescriptor proto mapping. */
export declare interface OutputPlugin {
  readonly pluginType: OutputPluginType;
  readonly args?: {};
}
