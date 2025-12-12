import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {User} from '../../../../lib/models/client';
import {CopyButton} from '../../copy_button';
import {Timestamp} from '../../timestamp';

/**
 * Component the details for a single User.
 */
@Component({
  selector: 'users-details',
  templateUrl: './users_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, CopyButton, Timestamp],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersDetails {
  readonly users = input.required<readonly User[]>();
}
