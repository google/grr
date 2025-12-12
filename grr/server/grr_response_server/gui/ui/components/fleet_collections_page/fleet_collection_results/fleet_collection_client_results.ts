import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input as routerInput,
} from '@angular/core';

import {PayloadType} from '../../../lib/models/result';
import {FlowStore} from '../../../store/flow_store';
import {CollectionResults} from '../../shared/collection_results/collection_results';
import {FlowResultsDownloadButton} from '../../shared/collection_results/flow_results_download_button/flow_results_download_button';

/** Component that displays results for a single client in a fleet collection. */
@Component({
  selector: 'fleet-collection-client-results',
  templateUrl: './fleet_collection_client_results.ng.html',
  styleUrls: ['./fleet_collection_client_results.scss'],
  imports: [CollectionResults, CommonModule, FlowResultsDownloadButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowStore],
})
export class FleetCollectionClientResults {
  protected readonly flowStore = inject(FlowStore);

  // TODO: These should be `required`, but tests are failing until
  // the bug is fixed.
  readonly fleetCollectionId = routerInput<string>();
  readonly clientId = routerInput<string>();
  readonly resultType = routerInput<PayloadType>();

  constructor() {
    effect(() => {
      const clientId = this.clientId();
      const fleetCollectionId = this.fleetCollectionId();
      const resultType = this.resultType();
      if (clientId && fleetCollectionId && resultType) {
        this.flowStore.initialize(clientId, fleetCollectionId);
        this.flowStore.fetchFlow();
        this.flowStore.fetchFlowResults(resultType);
      }
    });
  }
}
