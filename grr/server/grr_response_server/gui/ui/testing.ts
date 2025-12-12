import {NgModule, provideZoneChangeDetection} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {
  BrowserTestingModule,
  platformBrowserTesting,
} from '@angular/platform-browser/testing';

@NgModule({providers: [provideZoneChangeDetection()]})
export class ZoneChangeDetectionModule {}

/**
 * Initializes Angular test environment.
 */
export function initTestEnvironment() {
  try {
    TestBed.initTestEnvironment(
      [ZoneChangeDetectionModule, BrowserTestingModule],
      platformBrowserTesting(),
    );
  } catch (e) {
    // Ignore exceptions when calling it multiple times.
  }
}
