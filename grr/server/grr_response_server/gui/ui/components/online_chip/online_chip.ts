import {Component, Input, ChangeDetectionStrategy, OnChanges, SimpleChanges} from '@angular/core';
import {DateTime} from 'luxon';
import {interval, Subject, merge} from 'rxjs';
import {map} from 'rxjs/operators';

/**
 * Component displaying the status of a Client in a material chip.
 */
@Component({
  selector: 'online-chip',
  templateUrl: './online_chip.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnlineChip implements OnChanges {
  private static readonly STATUS_OFFLINE = 'offline';
  private static readonly STATUS_ONLINE = 'online';
  private static readonly ONLINE_TRESHOLD_MINUTES = 15;

  @Input() lastSeen?: Date;
  private readonly lastSeenChange$ = new Subject<void>();

  // status observable that updates every second and when lastSeen changes
  status$ = merge(interval(1000), this.lastSeenChange$).pipe(
    map(() => this.getStatus())
  );

  ngOnChanges(changes: SimpleChanges): void {
    this.lastSeenChange$.next();
  }

  getStatus(): string {
    if (this.lastSeen === undefined) {
      return OnlineChip.STATUS_OFFLINE;
    }

    const timeDiff = DateTime.local()
      .diff(DateTime.fromJSDate(this.lastSeen), 'minutes').as('minutes');
    if (timeDiff < OnlineChip.ONLINE_TRESHOLD_MINUTES) {
      return OnlineChip.STATUS_ONLINE;
    } else {
      return OnlineChip.STATUS_OFFLINE;
    }
  }
}
