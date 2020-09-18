import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {User} from '../../../lib/models/client';

/**
 * Component the details for a single User.
 */
@Component({
  selector: 'users-details',
  templateUrl: './users_details.ng.html',
  styleUrls: ['./users_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersDetails {
  @Input() users!: User[];
}
