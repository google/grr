import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input as routerInput,
} from '@angular/core';
import {MatTabsModule} from '@angular/material/tabs';
import {RouterModule} from '@angular/router';
import {FleetCollectionStore} from '../../store/fleet_collection_store';
import {ApprovalChip} from '../shared/approval_chip';

/** Component that displays details of a single fleet collection. */
@Component({
  selector: 'fleet-collection-details',
  templateUrl: './fleet_collection_details.ng.html',
  styleUrls: ['./fleet_collection_details.scss'],
  imports: [ApprovalChip, CommonModule, RouterModule, MatTabsModule],
  providers: [FleetCollectionStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionDetails {
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);

  // TODO: This input should be `required`, this would also allow
  // the store methods to receive string, instead of string | undefined, and
  // avoid null checks.
  readonly fleetCollectionId = routerInput<string>();

  constructor() {
    effect(() => {
      // Reset the store when the fleet collection id changes. The component is
      // not destroyed when navigating between fleet collections, so we need to
      // reset the store to avoid reusing the previous fleet collection's state.
      const fleetCollectionId = this.fleetCollectionId();
      if (fleetCollectionId) {
        this.fleetCollectionStore.initialize(fleetCollectionId);
      }
    });
    this.fleetCollectionStore.pollFleetCollection(this.fleetCollectionId);
    this.fleetCollectionStore.pollUntilAccess(this.fleetCollectionId);
    this.fleetCollectionStore.pollFleetCollectionApprovals(
      this.fleetCollectionId,
    );
  }
}
