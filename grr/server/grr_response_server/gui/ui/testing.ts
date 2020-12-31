import {TestBed} from '@angular/core/testing';
import {BrowserDynamicTestingModule, platformBrowserDynamicTesting} from '@angular/platform-browser-dynamic/testing';
import {DateTime} from '@app/lib/date_time';


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
        BrowserDynamicTestingModule, platformBrowserDynamicTesting());
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
