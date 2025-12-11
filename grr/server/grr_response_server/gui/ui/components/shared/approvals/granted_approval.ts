import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

import {Approval} from '../../../lib/models/user';
import {User} from '../../shared/user';

/**
 * Component to show granted approval for a client or hunt.
 */
@Component({
  selector: 'granted-approval',
  templateUrl: './granted_approval.ng.html',
  styleUrls: ['./approval_styles.scss'],
  imports: [CommonModule, MatIconModule, User],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GrantedApproval {
  readonly approval = input.required<Approval>();
}
