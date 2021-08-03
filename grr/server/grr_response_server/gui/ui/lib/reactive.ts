import {Observable, Subject} from 'rxjs';

/** ngOnDestroy callback that emits and completes an Observable. */
export interface OnDestroyObserver {
  (): void;
  /**
   * Observable that emits and completes when ngOnDestroy is called.
   */
  readonly triggered$: Observable<void>;
}

/**
 * Wraps an ngOnDestroy callback that emits and completes its `triggered$`
 * property when called.
 *
 * To use, add `implements OnDestroy` to your Component, Directive, or service.
 * Then, add `readonly ngOnDestroy = observeOnDestroy();`. You can now use it
 * like: `myObservable.pipe(takeUntil(this.ngOnDestroy.triggered$))`.
 *
 * @param ngOnDestroy an optional callback
 * @return ngOnDestroy function with `triggered$` property.
 */
export function observeOnDestroy(ngOnDestroy?: () => void): OnDestroyObserver {
  const subject = new Subject<void>();
  const handler = function ngOnDestroyHandler() {
    subject.next();
    subject.complete();
    ngOnDestroy?.();
  };
  handler.triggered$ = subject.asObservable();
  return handler;
}
