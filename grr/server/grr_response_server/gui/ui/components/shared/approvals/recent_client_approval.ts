import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {RouterModule} from '@angular/router';

import {ClientApproval} from '../../../lib/models/client';
import {ApprovalChip} from '../approval_chip';
import {OnlineChip} from '../online_chip';

/**
 * Displays a recent client approval.
 */
@Component({
  selector: 'recent-client-approval',
  templateUrl: './recent_client_approval.ng.html',
  styleUrls: ['./recent_client_approval.scss'],
  imports: [
    ApprovalChip,
    CommonModule,
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    OnlineChip,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecentClientApproval {
  readonly approval = input.required<ClientApproval>();
}
