import {ChangeDetectionStrategy, Component} from '@angular/core';
import {map} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';
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

  readonly client$ = this.clientPageFacade.selectedClient$;

  // TODO Move this to ClientDetailsStore
  readonly clientVersions$ = this.clientPageFacade.selectedClientVersions$.pipe(
      map(getClientVersions),
  );

  currentNumUsersShown = this.INITIAL_NUM_USERS_SHOWN;
  currentNumInterfacesShown = this.INITIAL_NUM_INTERFACES_SHOWN;
  currentNumVolumesShown = this.INITIAL_NUM_VOLUMES_SHOWN;

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
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
