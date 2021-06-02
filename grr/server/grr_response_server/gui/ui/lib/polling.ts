import {Observable, Subscription} from 'rxjs';


interface PollArgs<T> {
  readonly pollOn: Observable<unknown>;
  readonly pollEffect: () => void;
  readonly selector: Observable<T>;
  readonly pollUntil?: Observable<unknown>;
}

/**
 * Polls a side-effect and passes through emitted values.
 *
 * This function returns an Observable that, while being subscribed to:
 *
 * 1) Calls pollEffect() everytime `pollOn` emits. Use timer() for regular
 *    polling.
 * 2) Passes through `selector`.
 *
 * Both the polling and the subscription to selector are stopped, as soon as:
 * - `selector` completes, or
 * - the caller unsubscribes from poll(), or
 * - pollOn completes, or
 * - pollUntil emits.
 *
 * This function is designed to interoperate with RxJS:
 * - pollEffect() can trigger an RxJS effect that calls an API and updates
 *   the store.
 * - selector is a selector that reads from the updated store field.
 */
export function poll<T>(args: PollArgs<T>) {
  return new Observable<T>(subscriber => {
    let pollUntilSub: Subscription|undefined;
    let selectorSub: Subscription|undefined;
    let pollSub: Subscription|undefined;

    const unsubscribe = () => {
      pollSub?.unsubscribe();
      selectorSub?.unsubscribe();
      pollUntilSub?.unsubscribe();
    };

    pollSub = args.pollOn.subscribe({
      next() {
        args.pollEffect();
      },
      complete() {
        subscriber.complete();
        unsubscribe();
      }
    });

    selectorSub = args.selector.subscribe({
      next(v) {
        subscriber.next(v);
      },
      error(e) {
        subscriber.error(e);
      },
      complete() {
        subscriber.complete();
        unsubscribe();
      },
    });

    pollUntilSub = args.pollUntil?.subscribe({
      next() {
        subscriber.complete();
        unsubscribe();
      }
    });

    return unsubscribe;
  });
}
