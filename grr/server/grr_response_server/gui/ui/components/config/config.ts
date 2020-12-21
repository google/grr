import {Injectable} from '@angular/core';

declare global {
  interface Window {
    // These are references to external window definitions.
    // tslint:disable-next-line:enforce-name-casing
    __IS_GRR_TEST?: boolean;
    // tslint:disable-next-line:enforce-name-casing
    __IS_GRR_DEVELOPMENT?: boolean;
  }
}

/**
 * Global configuration settings.
 */
declare interface Config {
  readonly approvalPollingIntervalMs: number;
  readonly flowListPollingIntervalMs: number;
  readonly flowResultsPollingIntervalMs: number;
  readonly selectedClientPollingIntervalMs: number;
}

/**
 * Singleton providing access to global configuration settings.
 */
@Injectable({
  providedIn: 'root',
})
export class ConfigService {
  get config(): Config {
    if (window.__IS_GRR_TEST) {
      return {
        approvalPollingIntervalMs: 1000,
        flowListPollingIntervalMs: 1000,
        flowResultsPollingIntervalMs: 1000,
        selectedClientPollingIntervalMs: 1000,
      };
    } else {
      return {
        approvalPollingIntervalMs: 5000,
        flowListPollingIntervalMs: 5000,
        flowResultsPollingIntervalMs: 5000,
        selectedClientPollingIntervalMs: 5000,
      };
    }
  }
}
