/** Helper type that converts all optional fields to be required. */
export type Complete<T> = {
  [P in keyof Required<T>]:
      Pick<T, P> extends Required<Pick<T, P>>? T[P] : (T[P]|undefined);
};
