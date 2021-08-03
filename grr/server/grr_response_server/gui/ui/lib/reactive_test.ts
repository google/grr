// tslint:disable:g3-no-void-expression

import {Directive, OnDestroy} from '@angular/core';
import {initTestEnvironment} from '@app/testing';

import {observeOnDestroy} from './reactive';

initTestEnvironment();

// Test that observeOnDestroy() conforms to OnDestroy.
@Directive()
class TestComponent implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy();
}

describe('observeOnDestroy', () => {
  it('emits triggered$ when called', async () => {
    const instance = new TestComponent();
    const promise = new Promise<void>((resolve) => {
      instance.ngOnDestroy.triggered$.subscribe({next: resolve});
    });
    instance.ngOnDestroy();
    expect(await promise).toBeUndefined();
  });

  it('completes triggered$ when called', async () => {
    const instance = new TestComponent();
    instance.ngOnDestroy();

    const promise = new Promise<void>((resolve) => {
      instance.ngOnDestroy.triggered$.subscribe({complete: resolve});
    });
    expect(await promise).toBeUndefined();
  });

  it('invokes callback when called', async () => {
    @Directive()
    class CounterTestComponent {
      counter = 0;
      readonly ngOnDestroy = observeOnDestroy(() => {
        this.counter++;
      });
    }
    const instance = new CounterTestComponent();
    const instance2 = new CounterTestComponent();
    expect(instance.counter).toEqual(0);
    instance.ngOnDestroy();
    expect(instance.counter).toEqual(1);
    expect(instance2.counter).toEqual(0);
  });
});
