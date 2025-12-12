import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {User as ApiUser} from '../../../lib/api/api_interfaces';
import {translateUser} from '../../../lib/api/translation/client';
import {User} from '../../../lib/models/client';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {UsersDetails} from './data_renderer/users_details';

function usersPerClientIdFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): Map<string, User[]> {
  const usersPerClientId = new Map<string, User[]>();
  for (const result of collectionResults) {
    const clientId = result.clientId;
    const user = translateUser(result.payload as ApiUser);
    if (!usersPerClientId.has(clientId)) {
      usersPerClientId.set(clientId, []);
    }
    usersPerClientId.get(clientId)!.push(user);
  }
  return usersPerClientId;
}

/** Component that displays `Users` collection results. */
@Component({
  selector: 'users',
  templateUrl: './users.ng.html',
  imports: [CommonModule, CopyButton, UsersDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Users {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly usersPerClientId = computed(() =>
    usersPerClientIdFromCollectionResults(this.collectionResults()),
  );

  readonly isHuntResult = computed(() =>
    this.collectionResults().some((result) => isHuntResult(result)),
  );
}
