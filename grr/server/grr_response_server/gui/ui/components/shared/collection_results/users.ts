import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {User as ApiUser} from '../../../lib/api/api_interfaces';
import {translateUser} from '../../../lib/api/translation/client';
import {User} from '../../../lib/models/client';
import {CollectionResult} from '../../../lib/models/result';
import {UsersDetails} from './data_renderer/users_details';

function usersFromFlowResults(
  collectionResults: readonly CollectionResult[],
): readonly User[] {
  return collectionResults.map((result) => {
    return translateUser(result.payload as ApiUser);
  });
}

/** Component that displays `StatEntry` flow results. */
@Component({
  selector: 'users',
  templateUrl: './users.ng.html',
  imports: [CommonModule, UsersDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Users {
  readonly collectionResults = input.required<
    readonly User[],
    readonly CollectionResult[]
  >({
    transform: usersFromFlowResults,
  });
}
