import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {DateTime, Duration} from '@app/lib/date_time';
import {interval, merge, Subject} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

/**
 * Component displaying the status of a Client in a material chip.
 */
@Component({
  selector: 'online-chip',
  templateUrl: './online_chip.ng.html',
  styleUrls: ['./online_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnlineChip implements OnChanges {
  private static readonly STATUS_OFFLINE = 'offline';
  private static readonly STATUS_ONLINE = 'online';
  private static readonly ONLINE_THRESHOLD = Duration.fromObject({minutes: 15});

  @Input() lastSeen?: Date;
  private readonly lastSeenChange$ = new Subject<void>();

  // status observable that updates every second and when lastSeen changes
  status$ = merge(
                interval(1000),
                this.lastSeenChange$,
                )
                .pipe(
                    startWith(undefined),
                    map(() => this.getStatus()),
                );

  ngOnChanges(changes: SimpleChanges): void {
    this.lastSeenChange$.next();
  }

  getStatus(): string {
    if (this.lastSeen === undefined) {
      return OnlineChip.STATUS_OFFLINE;
    }

    const lastSeenLuxon = DateTime.fromJSDate(this.lastSeen);
    if (lastSeenLuxon.diffNow().negate() < OnlineChip.ONLINE_THRESHOLD) {
      return OnlineChip.STATUS_ONLINE;
    } else {
      return OnlineChip.STATUS_OFFLINE;
    }
  }
}
