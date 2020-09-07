import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {User} from '@app/lib/models/client';

/**
 * Component the details for a single User.
 */
@Component({
  selector: 'user-details',
  templateUrl: './user_details.ng.html',
  styleUrls: ['./user_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserDetails {
  @Input() user!: User;
}
