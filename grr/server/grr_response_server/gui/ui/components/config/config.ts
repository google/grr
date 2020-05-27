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
  flowListPollingIntervalMs: number;
  flowResultsPollingIntervalMs: number;
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
        flowListPollingIntervalMs: 100,
        flowResultsPollingIntervalMs: 100,
      };
    } else {
      return {
        flowListPollingIntervalMs: 5000,
        flowResultsPollingIntervalMs: 5000,
      };
    }
  }
}
