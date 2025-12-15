import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatListModule} from '@angular/material/list';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {Router, RouterModule} from '@angular/router';

import {ClientHistoryEntry, ClientStore} from '../../../store/client_store';
import {Timestamp} from '../../shared/timestamp';

/**
 * Component displaying the history of a Client.
 */
@Component({
  selector: 'client-history',
  templateUrl: './client_history.ng.html',
  styleUrls: ['./client_history.scss'],
  imports: [
    CommonModule,
    MatIconModule,
    MatListModule,
    MatTooltipModule,
    RouterModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientHistory {
  readonly clientStore = inject(ClientStore);
  private readonly router = inject(Router);

  constructor() {
    inject(Title).setTitle('GRR | Client > History');

    const initialNavigation = effect(() => {
      if (!this.router.url.endsWith('history')) {
        initialNavigation.destroy();
        return;
      }
      const history = this.clientStore.clientHistory();
      if (history.length > 0) {
        this.router.navigate([
          'clients',
          this.clientStore.clientId(),
          'history',
          this.historyTimestamp(history[0]),
        ]);
        initialNavigation.destroy();
      }
    });
  }

  historyTimestamp(history: ClientHistoryEntry): string {
    if (history.snapshot) {
      return String(history.snapshot.timestamp?.getTime() ?? '');
    }
    if (history.startupInfo) {
      return String(history.startupInfo.timestamp?.getTime() ?? '');
    }
    return '';
  }
}
