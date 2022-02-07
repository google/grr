/** Safety limits of a new hunt */
export declare interface SafetyLimits {
  readonly cpuLimit: bigint;
  readonly networkBytesLimit: bigint;
  readonly clientRate: number;
  readonly crashLimit: bigint;
  readonly avgResultsPerClientLimit: bigint;
  readonly avgCpuSecondsPerClientLimit: bigint;
  readonly avgNetworkBytesPerClientLimit: bigint;
  readonly expiryTime: bigint;
  readonly clientLimit?: bigint;
}
