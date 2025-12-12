import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input as routerInput,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {Title} from '@angular/platform-browser';
import {RouterModule} from '@angular/router';

import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {ApprovalRequest} from '../../shared/approvals/approval_request';
import {GrantedApproval} from '../../shared/approvals/granted_approval';
import {PendingApproval} from '../../shared/approvals/pending_approval';
import {FleetCollectionApprovalForm} from './fleet_collection_approval_form';

/** Component that displays approvals for fleet collection. */
@Component({
  selector: 'fleet-collection-approvals',
  templateUrl: './fleet_collection_approvals.ng.html',
  styleUrls: ['./fleet_collection_approvals.scss'],
  imports: [
    ApprovalRequest,
    CommonModule,
    FleetCollectionApprovalForm,
    GrantedApproval,
    MatButtonModule,
    MatDividerModule,
    PendingApproval,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionApprovals {
  protected readonly approvalRequestStore = inject(ApprovalRequestStore);
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);

  readonly fleetCollectionId = routerInput.required<string>();

  protected showForm = false;

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collection > Approvals');
  }
}
