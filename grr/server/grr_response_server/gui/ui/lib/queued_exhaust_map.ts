import { ObservableInput, OperatorFunction, ObservedValueOf, pipe, EMPTY } from 'rxjs';
import { concatMap, tap } from 'rxjs/operators';

/** TODO */
export function queuedExhaustMap<T, O extends ObservableInput<any>> (
  project: (value: T, index: number) => O
): OperatorFunction<T, ObservedValueOf<O>> {

  function recordLastRequest(value: T): void {

  }
  function isLastRequest(value: T): boolean {
    return true;
  }

  return pipe(
    tap((value) => {
      recordLastRequest(value);
    }),
    concatMap((value: T, index: number) => {
      if (isLastRequest(value)) {
        return project(value, index);
      } else {
        return EMPTY;
      }
    }),
  );
}
