import { ObservableInput, OperatorFunction, ObservedValueOf, pipe, EMPTY } from 'rxjs';
import { concatMap, tap, map } from 'rxjs/operators';

class NotImplementedError extends Error { };

interface RequestTracker<T> {
  recordLastTag(tag: T): void;
  shouldProcess(thisTag: T): boolean;
}

class SingleIndexTracker implements RequestTracker<number> {
  private lastIndex = -1;

  recordLastTag(tag: number): void {
    this.lastIndex = tag;
  }

  shouldProcess(thisTag: number): boolean {
    return this.lastIndex === thisTag;
  }
}

class ValueWithTag<V, T> {
  constructor(
    readonly value: V,
    readonly tag: T,
  ) { }
}

function tagByIndex<V>(indexTracker: SingleIndexTracker) {
  return pipe(
    map((value: V, index) => new ValueWithTag(value, index)),
    tap((valueWithTag: ValueWithTag<V, number>) => {
      indexTracker.recordLastTag(valueWithTag.tag);
    }),
  );
}

/**
 * Similar to exhaustMap, but buffers the specified number of most recent source values
 * in a queue of limited size. The source values that are not discarded are projected to
 * Observables and merged in the output Observable in a serialized fashion, waiting for
 * each one to complete before merging the next.
 *
 * Important notes:
 * - Currently only queue of size 1 is supported.
 * - If the source produces values faster than this operation discards them, no values will
 * be emitted.
 */
export function queuedExhaustMap<V, O extends ObservableInput<any>> (
  project: (value: V, index: number) => O, queueSize: 1 = 1
): OperatorFunction<V, ObservedValueOf<O>> {
  if (queueSize !== 1) {
    throw new NotImplementedError('Queue size different than 1 is not implemented yet.');
  }

  const requestTracker = new SingleIndexTracker();

  return pipe(
    tagByIndex(requestTracker),
    concatMap((valueWithTag, index) => {
      if (requestTracker.shouldProcess(valueWithTag.tag)) {
        return project(valueWithTag.value, index);
      } else {
        return EMPTY;
      }
    }),
  );
}
