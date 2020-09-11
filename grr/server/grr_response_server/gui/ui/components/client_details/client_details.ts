import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ClientDetailsFacade} from '@app/store/client_details_facade';
import {map} from 'rxjs/operators';

import {getClientVersions} from './client_diff';

/**
 * Component displaying the details for a single Client.
 */
@Component({
  selector: 'client-details',
  templateUrl: './client_details.ng.html',
  styleUrls: ['./client_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientDetails {
  // Not static & private because is referenced in the template
  readonly INITIAL_NUM_USERS_SHOWN = 1;
  readonly INITIAL_NUM_INTERFACES_SHOWN = 3;
  readonly INITIAL_NUM_VOLUMES_SHOWN = 2;

  readonly client$ = this.clientDetailsFacade.selectedClient$;

  // TODO(danielberbece): Move this to ClientDetailsStore.
  readonly clientVersions$ =
      this.clientDetailsFacade.selectedClientVersions$.pipe(
          map(getClientVersions),
      );

  currentNumUsersShown = this.INITIAL_NUM_USERS_SHOWN;
  currentNumInterfacesShown = this.INITIAL_NUM_INTERFACES_SHOWN;
  currentNumVolumesShown = this.INITIAL_NUM_VOLUMES_SHOWN;

  constructor(
      private readonly clientDetailsFacade: ClientDetailsFacade,
  ) {}

  getAccordionButtonState(
      totalNumElements: number, currentMaxNumElementsShown: number,
      initialMaxNumElementsShown: number): string {
    if (totalNumElements > currentMaxNumElementsShown) {
      return 'show-more';
    } else if (totalNumElements <= initialMaxNumElementsShown) {
      return 'no-button';
    }
    return 'show-less';
  }
}
