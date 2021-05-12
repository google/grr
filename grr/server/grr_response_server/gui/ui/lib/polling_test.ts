import {fakeAsync, tick} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {firstValueFrom, lastValueFrom, Subject} from 'rxjs';

import {poll} from './polling';


initTestEnvironment();

describe('poll', () => {
  it('polls the effect on subscription ', fakeAsync(() => {
       const pollEffect = jasmine.createSpy('pollEffect');

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect,
         selector: new Subject(),
       });

       expect(pollEffect).not.toHaveBeenCalled();

       const subscription = poll$.subscribe();

       tick(0);

       expect(pollEffect).toHaveBeenCalledTimes(1);

       tick(9);

       expect(pollEffect).toHaveBeenCalledTimes(1);

       tick(1);

       expect(pollEffect).toHaveBeenCalledTimes(2);

       tick(9);

       expect(pollEffect).toHaveBeenCalledTimes(2);

       tick(1);

       expect(pollEffect).toHaveBeenCalledTimes(3);

       subscription.unsubscribe();
     }));

  it('emits value from selector', fakeAsync(async () => {
       const selector = new Subject<string>();

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect: () => {
           selector.next('foobar');
         },
         selector,
       });

       const promise = firstValueFrom(poll$);

       tick(0);

       expect(await promise).toEqual('foobar');
     }));

  it('emits latest value from selector', fakeAsync(() => {
       const selector = new Subject<number>();
       let counter = 0;

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect: () => {
           selector.next(counter);
           counter += 1;
         },
         selector,
       });

       const emittedValues: number[] = [];
       const subscription = poll$.subscribe(v => {
         emittedValues.push(v);
       });

       tick(0);

       expect(emittedValues).toEqual([0]);

       tick(10);

       expect(emittedValues).toEqual([0, 1]);

       tick(10);

       expect(emittedValues).toEqual([0, 1, 2]);

       subscription.unsubscribe();
     }));


  it('stops polling after unsubscribe', fakeAsync(async () => {
       const selector = new Subject<string>();
       const pollEffect = jasmine.createSpy('pollEffect').and.callFake(() => {
         selector.next('foobar');
       });

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect,
         selector,
       });

       const promise = firstValueFrom(poll$);

       tick(0);

       expect(await promise).toEqual('foobar');

       tick(20);

       expect(pollEffect).toHaveBeenCalledTimes(1);
     }));

  it('continues polling while pollWhile() returns true', fakeAsync(() => {
       const pollEffect = jasmine.createSpy('pollEffect');

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect,
         selector: new Subject(),
         pollWhile: () => true,
       });

       const subscription = poll$.subscribe();

       tick(20);

       expect(pollEffect).toHaveBeenCalledTimes(3);

       subscription.unsubscribe();
     }));

  it('stops polling when pollWhile is false', fakeAsync(async () => {
       let counter = 0;
       const selector = new Subject<number>();
       const pollEffect = jasmine.createSpy('pollEffect').and.callFake(() => {
         selector.next(counter);
         counter += 1;
       });

       const poll$ = poll({
         pollIntervalMs: 10,
         pollEffect,
         selector,
         pollWhile: (value) => value < 1,
       });

       const promise = lastValueFrom(poll$);

       tick(30);

       expect(await promise).toEqual(1);

       expect(pollEffect).toHaveBeenCalledTimes(2);
     }));
});
