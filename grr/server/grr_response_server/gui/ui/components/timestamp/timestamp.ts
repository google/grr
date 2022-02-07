import {ChangeDetectionStrategy, Component, Injectable, Input, OnDestroy} from '@angular/core';
import {BehaviorSubject, combineLatest, Observable, timer} from 'rxjs';
import {distinctUntilChanged, map, mapTo, shareReplay, startWith, takeUntil} from 'rxjs/operators';

import {DateTime, Duration} from '../../lib/date_time';
import {observeOnDestroy} from '../../lib/reactive';

const MINUTE_THRESHOLD = Duration.fromObject({minutes: 1});

function computeRelative(jsDate: Date|null) {
  if (!jsDate) {
    return '';
  }

  const date = DateTime.fromJSDate(jsDate);
  const diff = date.diffNow();

  if (!diff.isValid) {
    return '';
  } else if (Math.abs(diff.valueOf()) < MINUTE_THRESHOLD.valueOf()) {
    return 'less than 1 minute ago';
  } else {
    return date.toRelative() ?? '';
  }
}

/**
 * String-based enum that defines the visibility of the relative timestamp (x
 * min ago).
 */
export type RelativeTimestampVisibility = 'visible'|'tooltip'|'hidden';

/**
 * Shows a formatted timestamp, based on the date received as parameter.
 */
@Component({
  selector: 'app-timestamp',
  templateUrl: './timestamp.ng.html',
  styleUrls: ['./timestamp.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Timestamp implements OnDestroy {
  @Input()
  set date(date: Date|undefined) {
    this.date$.next(date);
  }
  get date() {
    return this.date$.value;
  }
  @Input() relativeTimestamp: RelativeTimestampVisibility = 'tooltip';
  readonly timezone: string = 'UTC';

  readonly ngOnDestroy = observeOnDestroy(this);

  private readonly date$ = new BehaviorSubject<Date|undefined>(undefined);

  readonly relativeTimestampString$ =
      combineLatest([
        this.date$,
        this.timer.timer$.pipe(startWith(null)),
      ])
          .pipe(
              takeUntil(this.ngOnDestroy.triggered$),
              map(([date]) => date ? computeRelative(date) : ''),
              distinctUntilChanged(),
          );

  constructor(private readonly timer: TimestampRefreshTimer) {}
}

/** Timer that triggers the periodic refresh of Timestamp components. */
@Injectable({providedIn: 'root'})
export class TimestampRefreshTimer {
  readonly timer$: Observable<void> = timer(0, 10_000).pipe(
      mapTo(undefined),
      shareReplay({bufferSize: 1, refCount: true}),
  );
}
