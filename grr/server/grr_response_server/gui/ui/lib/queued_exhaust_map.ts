import { ObservableInput, OperatorFunction, ObservedValueOf, pipe, EMPTY } from 'rxjs';
import { concatMap, tap } from 'rxjs/operators';

class NotImplementedError extends Error { };

class RequestTracker<T> {
  lastValue?: T;
  isLastValueSet = false;

  recordLast(value: T): void {
    this.lastValue = value;
    this.isLastValueSet = true;
  }

  shouldProcess(value: T): boolean {
    return this.isLastValueSet && this.lastValue === value;
  }
}

/**
 * Similar to exhaustMap, but buffers the specified number of most recent source values
 * in a queue of limited size. The source values that are not discarded are projected to
 * Observables and merged in the output Observable in a serialized fashion, waiting for
 * each one to complete before merging the next.
 *
 * Currently only queue of size 1 is supported.
 */
export function queuedExhaustMap<T, O extends ObservableInput<any>> (
  project: (value: T, index: number) => O, queueSize: 1 = 1
): OperatorFunction<T, ObservedValueOf<O>> {
  if (queueSize !== 1) {
    throw new NotImplementedError('Queue size different than 1 is not implemented yet.');
  }

  const requestTracker = new RequestTracker<T>();

  return pipe(
    tap((value) => {
      requestTracker.recordLast(value);
    }),
    concatMap((value: T, index: number) => {
      if (requestTracker.shouldProcess(value)) {
        return project(value, index);
      } else {
        return EMPTY;
      }
    }),
  );
}
