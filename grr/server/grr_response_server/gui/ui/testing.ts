import {TestBed} from '@angular/core/testing';
import {BrowserDynamicTestingModule, platformBrowserDynamicTesting} from '@angular/platform-browser-dynamic/testing';

/**
 * Initializes Angular test environment.
 */
export function initTestEnvironment() {
  try {
    TestBed.initTestEnvironment(
        BrowserDynamicTestingModule, platformBrowserDynamicTesting());
  } catch (e) {
    // Ignore exceptions when calling it multiple times.
  }
}
