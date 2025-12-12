/**
 * Helper type that converts all optional fields to be required.
 */
export type Complete<T> = {
  [P in keyof T]-?: NonNullable<T[P]>;
};

/** Type that excludes primitive values that evaluate to false (0, "", ...) . */
export type Truthy<T> = Exclude<T, false | '' | 0 | null | undefined>;

/** Object where all keys must have truthy values. */
export type CompleteTruthy<T> = {
  [P in keyof T]-?: Truthy<T[P]>;
};

/** Enforce an object's key to be non-nullable. */
export type NonNullableKey<T, K extends keyof T> = Complete<Pick<T, K>> & T;

/** Enforce an object's key to be truthy. */
export type TruthyKey<T, K extends keyof T> = CompleteTruthy<Pick<T, K>> & T;

/** Mutates the Map, adding the given value to the Set at the given key. */
export function addToMapSetInPlace<K, V>(
  map: Map<K, Set<V>>,
  key: K,
  value: V,
) {
  let values = map.get(key);
  if (values === undefined) {
    values = new Set();
    map.set(key, values);
  }
  values.add(value);
}

/** Returns a CompareFn that compares two strings alphabetically. */
export function compareAlphabeticallyBy<T>(
  mapper: (value: T) => string,
): (a: T, b: T) => number {
  return (a, b) => mapper(a).localeCompare(mapper(b));
}

/** Returns a CompareFn that compares two Dates, ordering new to old. */
export function compareDateNewestFirst<T>(
  mapper: (value: T) => Date,
): (a: T, b: T) => number {
  return (a, b) => mapper(b).valueOf() - mapper(a).valueOf();
}

/** Converts a lowerCamelCase string to snake_case. */
export function camelToSnakeCase(str: string) {
  // Behavior for multiple succeeding uppercase letters and UpperCamelCase with
  // leading uppercase is NOT handled by special cases for now.
  return str.replace(/[A-Z]/g, (char) => `_${char.toLowerCase()}`);
}
