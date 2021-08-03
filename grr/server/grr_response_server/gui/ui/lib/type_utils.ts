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

type DeepReadonly<T> = T extends Array<infer U>?
    ReadonlyArray<DeepReadonly<U>>:
    {readonly[K in keyof T]: DeepReadonly<T[K]>};

/** Recursively freezes an object and all its members. */
export function deepFreeze<T>(object: T): DeepReadonly<T> {
  if (Object.isFrozen(object)) {
    return object as DeepReadonly<T>;
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

  return result as DeepReadonly<T>;
}
