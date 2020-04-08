import {AnyObject} from '@app/lib/api/api_interfaces';

/**
 * Constructs a Date from a unixtime string with microsecond-precision.
 *
 * Because `Date` uses millisecond-precision, microseconds are truncated.
 */
export function createDate(apiTimestamp: string): Date {
  if (!apiTimestamp) {
    throw new Error(`Date must not be empty.`);
  }
  const date = new Date(Number(apiTimestamp) / 1000);
  if (isNaN(date.valueOf())) {
    throw new Error(`Date "${apiTimestamp}" is invalid.`);
  }
  return date;
}

/**
 * Constructs a Date from a unixtime string with microsecond-precision.
 *
 * Because `Date` uses millisecond-precision, microseconds are truncated. This
 * function returns undefined when given undefined or the empty string.
 */
export function createOptionalDate(apiTimestamp: undefined): undefined;
export function createOptionalDate(apiTimestamp: ''): undefined;
export function createOptionalDate(apiTimestamp: string): Date;
export function createOptionalDate(apiTimestamp?: string): Date|undefined;

export function createOptionalDate(apiTimestamp?: string): Date|undefined {
  if (!apiTimestamp) {
    return undefined;  // Return undefined for undefined and empty string.
  }
  return createDate(apiTimestamp);
}

/**
 * Creates an unknown object out of protobuf's any object.
 * Unknown is different from any as, unlike any, it has to be explicitly cast
 * to a type for any use.
 */
export function createUnknownObject(anyObject?: AnyObject): unknown|undefined {
  if (!anyObject) {
    return undefined;
  }

  const result = {...anyObject};
  delete result['@type'];
  return result;
}
