import { of, from, Observable } from 'rxjs';
import { queuedExhaustMap } from './queued_exhaust_map';
import { delay } from 'rxjs/operators';
import { fakeAsync, tick } from '@angular/core/testing';

describe('queuedExhaustMap', () => {
  it('shouldn\'t discard anything if there is just one element (queue size 1)', () => {
    const valuePassed = 'dummy value';

    const singleValue$ = of(valuePassed).pipe(
      queuedExhaustMap((value) => {
        return of(value);
      }, 1),
    );

    const getLatestValues = emittedValuesWatcher(singleValue$);
    expect(getLatestValues()).toEqual([valuePassed]);
  });

  it('shouldn\'t discard anything if there are no concurrent elements (queue size 1)', () => {
    const repeatTimes = 10;
    const sentValues = Array(repeatTimes).map((_, index) => index);

    const manyValues$ = from(sentValues).pipe(
      queuedExhaustMap((value) => {
        return of(value);
      }, 1),
    );

    const getLatestValues = emittedValuesWatcher(manyValues$);
    expect(getLatestValues()).toEqual(sentValues);
  });

  it('should discard everything but the last concurrent element (queue size 1)', fakeAsync(() => {
    const blockTimeMs = 1000;

    const manyValuesWithDelay$ = of('initial', 'discarded1', 'discarded2', 'lastSaved').pipe(
      queuedExhaustMap((value) => {
        return of(value).pipe(
          delay(blockTimeMs),
        );
      }, 1),
    );

    const getLatestValues = emittedValuesWatcher(manyValuesWithDelay$);

    tick(blockTimeMs);
    expect(getLatestValues()).toEqual(['initial']);

    tick(blockTimeMs);
    expect(getLatestValues()).toEqual(['initial', 'lastSaved']);
  }));

  it(
    'should discard all but the last emissions of the same element concurrent with something else (queue size 1)',
    fakeAsync(() => {
      const blockTimeMs = 1000;
      const infTime = blockTimeMs * 100;
      const sameElement = 'this is repeated multiple times';

      const sameValueWithDelay$ = of(sameElement, sameElement, sameElement, sameElement).pipe(
        queuedExhaustMap((value) => {
          return of(value).pipe(
            delay(blockTimeMs),
          );
        }, 1),
      );

      const getLatestValues = emittedValuesWatcher(sameValueWithDelay$);

      tick(blockTimeMs);
      expect(getLatestValues()).toEqual([sameElement]);

      tick(blockTimeMs);
      expect(getLatestValues()).toEqual([sameElement, sameElement]);

      tick(infTime);
      expect(getLatestValues().length).toEqual(2);
    }));
});

function emittedValuesWatcher<T>(observable$: Observable<T>): () => ReadonlyArray<T> {
  const emittedValues: T[] = [];

  observable$.subscribe((value) => {
    emittedValues.push(value)
  });

  return () => emittedValues;
}
