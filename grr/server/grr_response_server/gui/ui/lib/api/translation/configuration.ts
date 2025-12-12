import {UiConfig} from '../../models/configuration';
import * as apiInterfaces from '../api_interfaces';
import {translateSafetyLimits} from './hunt';
import {translateOutputPlugin} from './output_plugin';

/** Constructs a UiConfig from the corresponding API data structure. */
export function translateUiConfig(
  uiConfig: apiInterfaces.ApiUiConfig,
): UiConfig {
  const defaultAccessDurationSeconds = Number(
    uiConfig.defaultAccessDurationSeconds,
  );
  const maxAccessDurationSeconds = Number(uiConfig.maxAccessDurationSeconds);

  return {
    ...uiConfig,
    safetyLimits: uiConfig.defaultHuntRunnerArgs
      ? translateSafetyLimits(uiConfig.defaultHuntRunnerArgs)
      : undefined,
    defaultOutputPlugins: (uiConfig.defaultOutputPlugins ?? []).map(
      translateOutputPlugin,
    ),
    defaultAccessDurationSeconds: !isNaN(defaultAccessDurationSeconds)
      ? defaultAccessDurationSeconds
      : undefined,
    maxAccessDurationSeconds: !isNaN(maxAccessDurationSeconds)
      ? maxAccessDurationSeconds
      : undefined,
  };
}
