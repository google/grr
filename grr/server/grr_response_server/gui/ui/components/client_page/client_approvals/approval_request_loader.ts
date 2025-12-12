import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input as routerInput,
} from '@angular/core';
import {RouterModule} from '@angular/router';

import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {ClientStore} from '../../../store/client_store';

/**
 * Component that triggers loading of an approval request.
 * The approval request can be displayed using the ApprovalRequest component.
 */
@Component({
  selector: 'approval-request-loader',
  template: '',
  imports: [RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalRequestLoader {
  private readonly clientStore = inject(ClientStore);
  private readonly approvalRequestStore = inject(ApprovalRequestStore);

  approvalId = routerInput<string | undefined>();
  requestor = routerInput<string | undefined>();

  constructor() {
    effect(() => {
      if (
        !this.approvalId() ||
        !this.clientStore.clientId() ||
        !this.requestor()
      ) {
        return;
      }
      this.approvalRequestStore.fetchClientApproval(
        this.approvalId()!,
        this.clientStore.clientId()!,
        this.requestor()!,
      );
    });
  }
}
