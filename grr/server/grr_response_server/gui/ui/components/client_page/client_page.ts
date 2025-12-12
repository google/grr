import {
  ChangeDetectionStrategy,
  Component,
  inject,
  Injector,
  Input as RouterInput,
} from '@angular/core';
import {MatTabsModule} from '@angular/material/tabs';
import {Title} from '@angular/platform-browser';
import {RouterModule} from '@angular/router';

import {ClientStore} from '../../store/client_store';
import {ClientOverview} from './client_overview';

/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  standalone: true,
  templateUrl: './client_page.ng.html',
  styleUrls: ['./client_page.scss'],
  imports: [ClientOverview, RouterModule, MatTabsModule],
  providers: [ClientStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientPage {
  readonly injector = inject(Injector);
  clientStore = inject(ClientStore);

  @RouterInput()
  set clientId(id: string) {
    this.clientStore.initialize(id);

    this.clientStore.pollFlows(this.clientStore.triggerFetchFlows, {
      injector: this.injector,
    });
    this.clientStore.pollScheduledFlows(
      this.clientStore.triggerFetchScheduledFlows,
      {injector: this.injector},
    );
    this.clientStore.pollClientApprovals();
  }

  constructor() {
    inject(Title).setTitle('GRR | Client');
  }
}
