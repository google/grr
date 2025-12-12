import {CommonModule, Location} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {Router} from '@angular/router';

import {ClientApproval, isClientApproval} from '../../../lib/models/client';
import {HuntApproval} from '../../../lib/models/hunt';
import {CopyButton} from '../../shared/copy_button';
import {User} from '../../shared/user';

/**
 * Component to show a pending approval for a client or hunt.
 */
@Component({
  selector: 'pending-approval',
  templateUrl: './pending_approval.ng.html',
  styleUrls: ['./approval_styles.scss'],
  imports: [CommonModule, CopyButton, MatIconModule, User],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PendingApproval {
  private readonly location = inject(Location);
  private readonly router = inject(Router);

  readonly approval = input.required<ClientApproval | HuntApproval>();

  protected readonly approvalUrl = computed((): string | null => {
    let urlTree: string[] = [];

    if (isClientApproval(this.approval())) {
      const approval = this.approval() as ClientApproval;
      urlTree = [
        'clients',
        approval.clientId,
        'approvals',
        approval.approvalId,
        'users',
        approval.requestor,
      ];
    } else {
      const approval = this.approval() as HuntApproval;
      urlTree = [
        'fleet-collections',
        approval.huntId,
        'approvals',
        approval.approvalId,
        'users',
        approval.requestor,
      ];
    }
    const pathTree = this.router.createUrlTree(urlTree);
    const url = new URL(window.location.origin);
    url.pathname = this.location.prepareExternalUrl(pathTree.toString());
    return url.toString();
  });
}
