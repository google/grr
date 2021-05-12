import {Observable, timer} from 'rxjs';


interface PollArgs<T> {
  readonly pollIntervalMs: number;
  readonly pollEffect: () => void;
  readonly selector: Observable<T>;
  readonly pollWhile?: (value: T) => boolean;
}

/**
 * Polls a side-effect and passes through emitted values.
 *
 * This function returns an Observable that, while being subscribed to:
 *
 * 1) Calls pollEffect() every `pollIntervalMs`, starting immediately upon
 *    subscription.
 * 2) Passes through `selector`.
 *
 * Both the polling and the subscription to selector are stopped, as soon as:
 * * `selector` completes, or
 * * the caller unsubscribes from poll(), or
 * * pollWhile() returns false.
 *
 * This function is designed to interoperate with RxJS:
 * * pollEffect() can trigger an RxJS effect that calls an API and updates
 *   the store.
 * * selector is a selector that reads from the updated store field.
 */
export function poll<T>(args: PollArgs<T>) {
  return new Observable<T>(subscriber => {
    const timerSub = timer(0, args.pollIntervalMs).subscribe(() => {
      args.pollEffect();
    });

    const selectorSub = args.selector.subscribe({
      next(v) {
        subscriber.next(v);

        if (args.pollWhile !== undefined && !args.pollWhile(v)) {
          unsubscribe();
          subscriber.complete();
        }
      },
      error(e) {
        subscriber.error(e);
      },
      complete() {
        timerSub.unsubscribe();
        subscriber.complete();
      },
    });

    const unsubscribe = () => {
      timerSub.unsubscribe();
      selectorSub.unsubscribe();
    };

    return unsubscribe;
  });
}
