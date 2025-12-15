import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {RouterModule} from '@angular/router';

import {ClientStore} from '../../../store/client_store';

/**
 * Component displaying a scheduled flow.
 */
@Component({
  selector: 'scheduled-flow',
  templateUrl: './scheduled_flow.ng.html',
  styleUrls: ['./scheduled_flow.scss'],
  imports: [CommonModule, MatButtonModule, RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScheduledFlow {
  protected readonly clientStore = inject(ClientStore);
}
