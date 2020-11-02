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

    const processedValues = getProcessedValues(singleValue$);
    expect(processedValues).toEqual([valuePassed]);
  });

  it('shouldn\'t discard anything if there are no concurrent elements (queue size 1)', () => {
    const repeatTimes = 10;
    const sentValues = Array(repeatTimes).map((_value, index) => index);

    const manyValues$ = from(sentValues).pipe(
      queuedExhaustMap((value) => {
        return of(value);
      }, 1),
    );

    const processedValues = getProcessedValues(manyValues$);
    expect(processedValues).toEqual(sentValues);
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

    const processedValues = getProcessedValues(manyValuesWithDelay$);

    tick(blockTimeMs);
    expect(processedValues).toEqual(['initial']);

    tick(blockTimeMs);
    expect(processedValues).toEqual(['initial', 'lastSaved']);
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

      const processedValues = getProcessedValues(sameValueWithDelay$);

      tick(blockTimeMs);
      expect(processedValues).toEqual([sameElement]);

      tick(blockTimeMs);
      expect(processedValues).toEqual([sameElement, sameElement]);

      tick(infTime);
      expect(processedValues.length).toEqual(2);
    }));
});

function getProcessedValues<T>(observable$: Observable<T>) {
  const processedValues = Array();
  observable$.subscribe((value) => {
    processedValues.push(value)
  });
  return processedValues;
}
