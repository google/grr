import {ComponentHarness} from '@angular/cdk/testing';

import {UsersDetailsHarness} from '../data_renderer/testing/users_details_harness';

/** Harness for the Users component. */
export class UsersHarness extends ComponentHarness {
  static hostSelector = 'users';

  readonly clientId = this.locatorForAll('.client-id');
  readonly usersDetails = this.locatorForAll(UsersDetailsHarness);
}
