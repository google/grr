import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {interval, merge, Subject} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {isClientOnline} from '../../lib/models/client';

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
  @Input() lastSeen?: Date;
  private readonly lastSeenChange$ = new Subject<void>();

  // status observable that updates every second and when lastSeen changes
  readonly status$ = merge(
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

  getStatus() {
    if (this.lastSeen === undefined || !isClientOnline(this.lastSeen)) {
      return 'offline';
    } else {
      return 'online';
    }
  }
}
