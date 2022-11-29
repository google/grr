/** Map from OutputPlugin name to OutputPluginDescriptor. */
export type OutputPluginDescriptorMap =
    ReadonlyMap<string, OutputPluginDescriptor>;

/** Combine both OutputPlugin and OutputPluginDescriptor from the backend */
export interface OutputPluginDescriptor {
  readonly name: string;
  readonly description: string;
  readonly argsType: string;
}