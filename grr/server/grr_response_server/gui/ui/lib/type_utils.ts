/** Helper type that converts all optional fields to be required. */
export type Complete<T> = {
  [P in keyof T] -?: NonNullable<T[P]>;
};

type Falsey = false|''|0|null|undefined;

/** Type that excludes primitive values that evaluate to false (0, "", ...) . */
export type Truthy<T> = Exclude<T, Falsey>;

/** Object where all keys must have truthy values. */
export type CompleteTruthy<T> = {
  [P in keyof T] -?: Truthy<T[P]>;
};

/** Enforce an object's key to be non-nullable. */
export type NonNullableKey<T, K extends keyof T> = Complete<Pick<T, K>>&T;

/** Enforce an object's key to be truthy. */
export type TruthyKey<T, K extends keyof T> = CompleteTruthy<Pick<T, K>>&T;

/** Allow overwriting an object's readonly keys (for tests). */
export type Writable<T> = {
  -readonly[K in keyof T]: T[K];
};

/** Allow all keys and all keys of nested objects to be undefined. */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends Array<infer U>? Array<DeepPartial<U>>:
                                                DeepPartial<T[P]>
};

type DeepReadonly<T> = T extends Array<infer U>?
    ReadonlyArray<DeepReadonly<U>>:
    {readonly[K in keyof T]: DeepReadonly<T[K]>};


/** Recursively freezes an object and all its members. */
export function deepFreeze<T>(object: T): DeepReadonly<T> {
  if (Object.isFrozen(object)) {
    return object as unknown as DeepReadonly<T>;
  }

  // Freeze main object first to prevent infinite loop with circular references.
  const result = Object.freeze(object);

  const properties = [
    ...Object.getOwnPropertyNames(result),
    ...Object.getOwnPropertySymbols(result),
  ] as Array<keyof T>;

  for (const property of properties) {
    // tslint:disable-next-line:no-dict-access-on-struct-type
    const value = object[property];

    if (value && typeof value === 'object') {
      deepFreeze(value);
    }
  }

  return result as unknown as DeepReadonly<T>;
}

/** Creates an ArrayBuffer from an Array of uint8s. */
export const arrayBufferOf = (bytes: number[]) => new Uint8Array(bytes).buffer;

/** Merges all key-value entries from all given Maps. */
export function mergeMaps<K, V>(
    ...maps: ReadonlyArray<ReadonlyMap<K, V>|Map<K, V>|null|undefined>):
    ReadonlyMap<K, V> {
  return new Map(maps.flatMap(map => map ? [...map] : []));
}

/**
 * Converts an Array to a Map by mapping entries to keys using the provided
 * keyMapper function.
 */
export function toMap<I, K>(
    entries: ReadonlyArray<I>, keyMapper: ((entry: I) => K)): Map<K, I>;
export function toMap<I, K, V>(
    entries: ReadonlyArray<I>,
    keyMapper: ((entry: I) => K),
    valueMapper: ((entry: I) => V),
    ): Map<K, V>;
export function toMap<I, K, V>(
    entries: ReadonlyArray<I>,
    keyMapper: ((entry: I) => K),
    valueMapper?: ((entry: I) => V),
) {
  const mapper = valueMapper ?? ((v) => v);
  return new Map(entries.map(entry => [keyMapper(entry), mapper(entry)]));
}

/** Returns a new Map containing all `map` entries and the additional entry. */
export function addToMap<K, V>(
    map: ReadonlyMap<K, V>|Map<K, V>|null|undefined, key: K,
    value: V): ReadonlyMap<K, V> {
  return new Map([...(map ?? []), [key, value]]);
}

/** Mutates the Map, adding the given value to the Set at the given key. */
export function addToMapSetInPlace<K, V>(
    map: Map<K, Set<V>>, key: K, value: V) {
  let values = map.get(key);
  if (values === undefined) {
    values = new Set();
    map.set(key, values);
  }
  values.add(value);
}

/** Returns a new Map with identical keys and transformed values. */
export function transformMapValues<K, V1, V2>(
    map: ReadonlyMap<K, V1>,
    mapper: ((value: V1, key: K) => V2)): ReadonlyMap<K, V2> {
  return new Map(
      Array.from(map.entries()).map(([key,
                                      value]) => [key, mapper(value, key)]));
}

/** Returns a CompareFn that compares two strings alphabetically. */
export function compareAlphabeticallyBy<T>(mapper: (value: T) => string):
    ((a: T, b: T) => number) {
  return (a, b) => mapper(a).localeCompare(mapper(b));
}

/** Returns a CompareFn that compares two Dates, ordering old to new. */
export function compareDateOldestFirst<T>(mapper: (value: T) => Date):
    ((a: T, b: T) => number) {
  return (a, b) => mapper(a).valueOf() - mapper(b).valueOf();
}

/** Returns a CompareFn that compares two Dates, ordering new to old. */
export function compareDateNewestFirst<T>(mapper: (value: T) => Date):
    ((a: T, b: T) => number) {
  return (a, b) => mapper(b).valueOf() - mapper(a).valueOf();
}

/** Converts a lowerCamelCase string to snake_case. */
export function camelToSnakeCase(str: string) {
  // Behavior for multiple succeeding uppercase letters and UpperCamelCase with
  // leading uppercase is NOT handled by special cases for now.
  return str.replace(/[A-Z]/g, char => `_${char.toLowerCase()}`);
}

/** Callback for `ControlValueAccessor.registerOnChange`. */
export type OnChangeFn<T> = (value: T) => void;

/** Callback for `ControlValueAccessor.registerOnTouched`. */
export type OnTouchedFn = () => void;

/** Capitalizes a string by turning the first character uppercase. */
export function capitalize(v: string): string {
  return v[0].toUpperCase() + v.slice(1);
}
