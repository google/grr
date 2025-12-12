import {
  AdminUIClientWarningsConfigOption,
  AdminUIHuntConfig,
  HuntRunnerArgs,
} from '../api/api_interfaces';
import {SafetyLimits} from './hunt';
import {OutputPlugin} from './output_plugin';

/**
 * UiConfig encapsulates configuration information for the UI.
 */
export interface UiConfig {
  readonly heading?: string;
  readonly reportUrl?: string;
  readonly helpUrl?: string;
  readonly grrVersion?: string;
  readonly profileImageUrl?: string;
  readonly defaultHuntRunnerArgs?: HuntRunnerArgs;
  readonly safetyLimits?: SafetyLimits;
  readonly huntConfig?: AdminUIHuntConfig;
  readonly defaultOutputPlugins?: OutputPlugin[];
  readonly clientWarnings?: AdminUIClientWarningsConfigOption;
  readonly defaultAccessDurationSeconds?: number;
  readonly maxAccessDurationSeconds?: number;
}
