import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';
import {RouterModule} from '@angular/router';

import {isClientApproval} from '../../../lib/models/client';
import {isHuntApproval} from '../../../lib/models/hunt';
import {Approval} from '../../../lib/models/user';
import {HumanReadableDurationPipe} from '../../../pipes/human_readable/human_readable_duration_pipe';
import {GlobalStore} from '../../../store/global_store';
import {Timestamp} from '../timestamp';
import {User} from '../user';

/** Component that displays the approval request stored in the ApprovalRequestStore. */
@Component({
  selector: 'approval-request',
  templateUrl: './approval_request.ng.html',
  styleUrls: ['./approval_request.scss'],
  imports: [
    CommonModule,
    HumanReadableDurationPipe,
    MatButtonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    RouterModule,
    Timestamp,
    User,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalRequest {
  protected readonly globalStore = inject(GlobalStore);

  readonly approval = input.required<Approval>();
  readonly grantApproval = output<void>();

  protected readonly isClientApproval = isClientApproval;
  protected readonly isHuntApproval = isHuntApproval;

  protected readonly canGrant = computed(() => {
    const user = this.globalStore.currentUser();
    return (
      this.approval() &&
      user &&
      user.name !== this.approval().requestor &&
      !this.approval().approvers.includes(user.name)
    );
  });

  protected readonly longExpiration = computed(() => {
    const expirationTime = this.approval()?.expirationTime;
    if (!expirationTime) return false;

    const defaultAccessDurationSeconds =
      this.globalStore.uiConfig()?.defaultAccessDurationSeconds;
    if (!defaultAccessDurationSeconds) return false;

    const accessDurationMillis =
      expirationTime.getTime() - new Date().getTime();
    return accessDurationMillis > defaultAccessDurationSeconds * 1000;
  });
}
