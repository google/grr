import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input as routerInput,
} from '@angular/core';
import {RouterModule} from '@angular/router';

import {ApprovalRequestStore} from '../../../store/approval_request_store';

/**
 * Component that triggers loading of an fleet collection approval request.
 * The approval request can be displayed using the ApprovalRequest component.
 */
@Component({
  selector: 'fleet-collection-approval-request-loader',
  template: '',
  imports: [RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionApprovalRequestLoader {
  private readonly approvalRequestStore = inject(ApprovalRequestStore);

  fleetCollectionId = routerInput<string | undefined>();
  approvalId = routerInput<string | undefined>();
  requestor = routerInput<string | undefined>();

  constructor() {
    effect(() => {
      if (
        !this.approvalId() ||
        !this.fleetCollectionId() ||
        !this.requestor()
      ) {
        return;
      }
      this.approvalRequestStore.fetchFleetCollectionApproval(
        this.approvalId()!,
        this.fleetCollectionId()!,
        this.requestor()!,
      );
    });
  }
}
