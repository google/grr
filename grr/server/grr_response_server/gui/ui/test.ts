// g3-prettier-ignore-file
// This file is required by karma.conf.js and loads recursively all the .spec
// and framework files

// NOTE: the order of imports is important. zone.js/dist/zome-testing has
// to be imported before any of the Angular modules, otherwise the tests
// will fail. More context here:
// https://github.com/angular/angular/issues/40305
import 'zone.js/dist/zone-testing';
import {getTestBed} from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

// First, initialize the Angular testing environment.
getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
);
