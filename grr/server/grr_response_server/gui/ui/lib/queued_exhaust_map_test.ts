import {fakeAsync, tick as angularTick} from '@angular/core/testing';
import {asyncScheduler, from, Observable, of} from 'rxjs';
import {delay} from 'rxjs/operators';

import {initTestEnvironment} from '../testing';

import {queuedExhaustMap} from './queued_exhaust_map';


initTestEnvironment();


describe('queuedExhaustMap', () => {
  let tick: (milliseconds: number) => void;
  let oldNow: () => number;

  // See https://stackoverflow.com/questions/50759469/how-do-i-mock-rxjs-6-timer
  // for the context.
  // TODO(user): we should convert this into a more generic utility
  // function.
  beforeEach(() => {
    let fakeNow = 0;
    tick = millis => {
      fakeNow += millis;
      angularTick(millis);
    };

    oldNow = asyncScheduler.now;
    asyncScheduler.now = () => fakeNow;
  });

  afterEach(() => {
    asyncScheduler.now = oldNow;
  });

  it('shouldn\'t discard anything if there is just one element (queue size 1)',
     () => {
       const valuePassed = 'dummy value';

       const singleValue$ = of(valuePassed)
                                .pipe(
                                    queuedExhaustMap(
                                        (value) => {
                                          return of(value);
                                        },
                                        1),
                                );

       const getLatestValues = emittedValuesWatcher(singleValue$);
       expect(getLatestValues()).toEqual([valuePassed]);
     });

  it('shouldn\'t discard anything if there are no concurrent elements (queue size 1)',
     () => {
       const repeatTimes = 10;
       const sentValues = Array.from<number>({length: repeatTimes})
                              .map((value, index) => index);

       const manyValues$ = from(sentValues)
                               .pipe(
                                   queuedExhaustMap(
                                       (value) => {
                                         return of(value);
                                       },
                                       1),
                               );

       const getLatestValues = emittedValuesWatcher(manyValues$);
       expect(getLatestValues()).toEqual(sentValues);
     });

  it('should discard everything but the last concurrent element (queue size 1)',
     fakeAsync(() => {
       const blockTimeMs = 1000;

       const manyValuesWithDelay$ =
           of('initial', 'discarded1', 'discarded2', 'lastSaved')
               .pipe(
                   queuedExhaustMap(
                       (value) => {
                         return of(value).pipe(
                             delay(blockTimeMs),
                         );
                       },
                       1),
               );

       const getLatestValues = emittedValuesWatcher(manyValuesWithDelay$);

       tick(blockTimeMs);
       expect(getLatestValues()).toEqual(['initial']);

       tick(blockTimeMs);
       expect(getLatestValues()).toEqual(['initial', 'lastSaved']);
     }));

  it('should discard all but the last emissions of the same element concurrent with something else (queue size 1)',
     fakeAsync(() => {
       const blockTimeMs = 1000;
       const infTime = blockTimeMs * 100;
       const sameElement = 'this is repeated multiple times';

       const sameValueWithDelay$ =
           of(sameElement, sameElement, sameElement, sameElement)
               .pipe(
                   queuedExhaustMap(
                       (value) => {
                         return of(value).pipe(
                             delay(blockTimeMs),
                         );
                       },
                       1),
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

function emittedValuesWatcher<T>(observable$: Observable<T>): () =>
    ReadonlyArray<T> {
  const emittedValues: T[] = [];

  observable$.subscribe((value) => {
    emittedValues.push(value);
  });

  return () => emittedValues;
}
