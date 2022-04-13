import {TestBed} from '@angular/core/testing';
import {BrowserDynamicTestingModule, platformBrowserDynamicTesting} from '@angular/platform-browser-dynamic/testing';
import {ActivatedRoute, Router} from '@angular/router';
import {NEVER} from 'rxjs';

import {TimestampRefreshTimer} from './components/timestamp/timestamp';
import {DateTime} from './lib/date_time';

/** Implements an equality tester for luxon's DateTime objects. */
export function dateTimeEqualityTester(
    first: unknown, second: unknown): boolean|void {
  if (first instanceof DateTime && second instanceof DateTime) {
    return first.valueOf() === second.valueOf();
  }
}

/**
 * Initializes Angular test environment.
 */
export function initTestEnvironment() {
  try {
    TestBed.initTestEnvironment(
        BrowserDynamicTestingModule, platformBrowserDynamicTesting(),
        {teardown: {destroyAfterEach: false}});
  } catch (e) {
    // Ignore exceptions when calling it multiple times.
  }
}

/** Removes keys with value `undefined` to make testing of objects easier. */
export function removeUndefinedKeys<T>(obj: T[]): T[];
export function removeUndefinedKeys<T>(obj: T): Partial<T>|T;
export function removeUndefinedKeys<T>(obj: T|T[]): T|Partial<T>|T[] {
  if (Array.isArray(obj)) {
    return obj.map<T>(removeUndefinedKeys);
  } else if (obj === null) {
    return obj;
  } else if (typeof obj === 'object' && (obj as {}).constructor === Object) {
    // TODO: Type '{ [k: string]: any; }' is not assignable to type
    // 'T | Partial<T> | T[]'.
    return Object.fromEntries(Object.entries(obj)
                                  .filter(([, value]) => value !== undefined)
                                  .map(([key, value]) => ([
                                         key, removeUndefinedKeys(value)
                                         // OSS code.
                                         // tslint:disable-next-line:no-any
                                       ]))) as any;
  } else {
    return obj;
  }
}

/**
 * Returns a sensible route for testing.
 *
 * The root route '' is rarely what we want to inject in a Component for
 * testing. if tests need a component to access a route, this is likely the
 * first child component
 */
export function getActivatedChildRoute(): ActivatedRoute {
  const router = TestBed.inject(Router);
  return router.routerState.root.firstChild ?? router.routerState.root;
}

/**
 * Returns a timer that never emits.
 *
 * Sometimes tests of components that include <app-timestamp /> fail with errors
 * like:
 * - "Error: 1 periodic timer(s) still in the queue."
 * - "Error: Timeout - Async function did not complete within 5000ms"
 *
 * In these cases, try disabling the timer by adding this provider to the
 * TestBed module configuration.
 */
export const DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER = {
  provide: TimestampRefreshTimer,
  useFactory: () => ({timer$: NEVER}),
} as const;
