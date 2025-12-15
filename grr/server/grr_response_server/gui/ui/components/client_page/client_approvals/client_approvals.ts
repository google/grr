import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {Title} from '@angular/platform-browser';
import {RouterModule} from '@angular/router';

import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {ClientStore} from '../../../store/client_store';
import {ApprovalRequest} from '../../shared/approvals/approval_request';
import {GrantedApproval} from '../../shared/approvals/granted_approval';
import {PendingApproval} from '../../shared/approvals/pending_approval';
import {ClientApprovalForm} from './client_approval_form';

/**
 * Component to request approval for the current client.
 */
@Component({
  selector: 'client-approvals',
  templateUrl: './client_approvals.ng.html',
  styleUrls: ['./client_approvals.scss'],
  imports: [
    ApprovalRequest,
    ClientApprovalForm,
    CommonModule,
    GrantedApproval,
    MatButtonModule,
    MatDividerModule,
    PendingApproval,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientApprovals {
  protected readonly clientStore = inject(ClientStore);
  protected readonly approvalRequestStore = inject(ApprovalRequestStore);

  protected showForm = false;

  constructor() {
    inject(Title).setTitle('GRR | Client > Approvals');
  }
}
