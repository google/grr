import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import {takeUntilDestroyed} from '@angular/core/rxjs-interop';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {interval} from 'rxjs';

import {isClientOnline} from '../../lib/models/client';

/**
 * Component displaying the status of a Client in a material chip.
 */
@Component({
  selector: 'online-chip',
  templateUrl: './online_chip.ng.html',
  imports: [CommonModule, MatChipsModule, MatIconModule],
  styleUrls: ['./online_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OnlineChip {
  readonly lastSeen = input<Date | undefined>();
  /**
   * The status of the client. A client is considered online if it has been
   * seen in the last 15 minutes based on the lastSeen date. If the lastSeen
   * date is undefined, the client is considered offline.
   */
  readonly status = signal<'online' | 'offline' | undefined>(undefined);

  constructor() {
    effect(() => {
      this.updateStatus(this.lastSeen());
    });

    // Update the online/offline status every 10 seconds.
    interval(10000)
      .pipe(takeUntilDestroyed(inject(DestroyRef)))
      .subscribe(() => {
        this.updateStatus(this.lastSeen());
      });
  }

  private updateStatus(lastSeen: Date | undefined) {
    this.status.set(
      lastSeen == null || !isClientOnline(lastSeen) ? 'offline' : 'online',
    );
  }
}
