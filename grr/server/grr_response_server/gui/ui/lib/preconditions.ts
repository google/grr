import {NonNullableKey, Truthy, TruthyKey} from './type_utils';

/** Error that indicates violated preconditions. */
export class PreconditionError extends Error {}

// tslint:disable-next-line:no-any
function getTypeName(obj: any): string {
  return obj?.constructor?.name ?? typeof obj;
}

/** Type guard that returns true if the value is neither null nor undefined. */
export function isNonNull<T>(value: T): value is NonNullable<T> {
  return value !== null && value !== undefined;
}

/** Throws PreconditionError if value is null or undefined. */
export function assertNonNull<T>(
    value: T, name: string = 'value'): asserts value is NonNullable<T> {
  if (value === null || value === undefined) {
    throw new PreconditionError(`Expected ${name} to be non-nullable, but got ${
        JSON.stringify(value)} of type ${getTypeName(value)}.`);
  }
}

/** Throws PreconditionError if value evaluates to false. */
export function assertTruthy<T>(
    value: T, name: string = 'value'): asserts value is Truthy<T> {
  if (!value) {
    throw new PreconditionError(`Expected ${name} to be truthy, but got ${
        JSON.stringify(value)} of type ${getTypeName(value)}.`);
  }
}

/** Throws PreconditionError if the value's key is null or undefined. */
export function assertKeyNonNull<T, K extends keyof T>(
    value: T, key: K): asserts value is NonNullableKey<T, K> {
  assertNonNull(value[key], `key ${key}`);
}

/** Throws PreconditionError if the value's key evaluates to false. */
export function assertKeyTruthy<T, K extends keyof T>(
    value: T, key: K): asserts value is TruthyKey<T, K> {
  assertTruthy(value[key], `key ${key}`);
}
