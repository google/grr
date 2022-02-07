import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {filter, takeUntil} from 'rxjs/operators';

import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientDetailsGlobalStore} from '../../store/client_details_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';

/**
 * Component displaying the details for a single Client.
 */
@Component({
  selector: 'client-details',
  templateUrl: './client_details.ng.html',
  styleUrls: ['./client_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientDetails implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  // Not static & private because is referenced in the template
  readonly INITIAL_NUM_USERS_SHOWN = 1;
  readonly INITIAL_NUM_INTERFACES_SHOWN = 3;
  readonly INITIAL_NUM_VOLUMES_SHOWN = 2;

  readonly clientVersions$ =
      this.clientDetailsGlobalStore.selectedClientVersions$;

  currentNumUsersShown = this.INITIAL_NUM_USERS_SHOWN;
  currentNumInterfacesShown = this.INITIAL_NUM_INTERFACES_SHOWN;
  currentNumVolumesShown = this.INITIAL_NUM_VOLUMES_SHOWN;

  constructor(
      private readonly clientDetailsGlobalStore: ClientDetailsGlobalStore,
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
  ) {
    this.selectedClientGlobalStore.clientId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            )
        .subscribe(clientId => {
          this.clientDetailsGlobalStore.selectClient(clientId);
        });
  }

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
