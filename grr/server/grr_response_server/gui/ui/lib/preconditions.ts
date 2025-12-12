import {NonNullableKey, Truthy, TruthyKey} from './type_utils';

/** Error that indicates violated preconditions. */
export class PreconditionError extends Error {}

// tslint:disable-next-line:no-any
function getTypeName(obj: any): string {
  return obj?.constructor?.name ?? typeof obj;
}

/** Throws PreconditionError if value is null or undefined. */
export function assertNonNull<T>(
  value: T,
  name: string = 'value',
): asserts value is NonNullable<T> {
  if (value === null || value === undefined) {
    throw new PreconditionError(
      `Expected ${name} to be non-nullable, but got ${JSON.stringify(
        value,
      )} of type ${getTypeName(value)}.`,
    );
  }
}

/** Throws PreconditionError if value evaluates to false. */
export function assertTruthy<T>(
  value: T,
  name: string = 'value',
): asserts value is Truthy<T> {
  if (!value) {
    throw new PreconditionError(
      `Expected ${name} to be truthy, but got ${JSON.stringify(
        value,
      )} of type ${getTypeName(value)}.`,
    );
  }
}

/** Throws PreconditionError if the value's key is null or undefined. */
export function assertKeyNonNull<T, K extends keyof T>(
  value: T,
  key: K,
): asserts value is NonNullableKey<T, K> {
  assertNonNull(value[key], `key ${String(key)}`);
}

/** Throws PreconditionError if the value's key evaluates to false. */
export function assertKeyTruthy<T, K extends keyof T>(
  value: T,
  key: K,
): asserts value is TruthyKey<T, K> {
  assertTruthy(value[key], `key ${String(key)}`);
}

interface StringEnum<T> {
  [id: string]: T | string;
}

/** Returns true if the given string value is present in an enum. */
export function isEnum<T extends string>(
  value: string,
  enumType: StringEnum<T>,
): value is T {
  return Object.values(enumType).some((enumVal) => enumVal === value);
}

/**
 * Throws PreconditionError if the given string value is not present in the
 * enum.
 */
export function assertEnum<T extends string>(
  value: string | undefined,
  enumType: StringEnum<T>,
): asserts value is T {
  if (value === undefined || !isEnum(value, enumType)) {
    const values = Object.values(enumType).join(', ');
    throw new PreconditionError(
      `Expected "${value}" to be a member of enum ${values}.`,
    );
  }
}

/** Throws PreconditionError if the value is not a number. */
export function assertNumber<T>(value: number | T): asserts value is number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new PreconditionError(
      `Expected ${value} to be able to convert to number, but got ${JSON.stringify(
        value,
      )} of type ${getTypeName(value)}.`,
    );
  }
}
