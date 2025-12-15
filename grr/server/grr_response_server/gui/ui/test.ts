// g3-prettier-ignore-file
// This file is required by karma.conf.js and loads recursively all the .spec
// and framework files

// NOTE: the order of imports is important. zone.js/testing has
// to be imported before any of the Angular modules, otherwise the tests
// will fail. More context here:
// https://github.com/angular/angular/issues/40305

// zone.js is not found if not specified with the file extension.
// tslint:disable-next-line:ban-malformed-import-paths
import 'zone.js';
import 'zone.js/testing';

import {provideZoneChangeDetection, NgModule} from '@angular/core';
import {getTestBed} from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

// First, initialize the Angular testing environment.
@NgModule({ providers: [ provideZoneChangeDetection() ] })
export class ZoneChangeDetectionModule {}


getTestBed().initTestEnvironment(
  [ZoneChangeDetectionModule, BrowserDynamicTestingModule],
  platformBrowserDynamicTesting(),
);
