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

/** Recursively removes the readonly modifier of fields */
export type DeepMutable<T> = {
  -readonly[P in keyof T]:
  T[P] extends (infer U)[] ? DeepMutable<U>[] :
  T[P] extends Date ? T[P] :
  T[P] extends object ? DeepMutable<T[P]> :
  T[P];
};
