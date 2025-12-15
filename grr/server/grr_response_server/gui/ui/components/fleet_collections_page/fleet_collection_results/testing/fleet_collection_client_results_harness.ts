import {ComponentHarness} from '@angular/cdk/testing';

import {FlowResultsDownloadButtonHarness} from '../../../shared/collection_results/flow_results_download_button/testing/flow_results_download_button_harness';
import {CollectionResultsHarness} from '../../../shared/collection_results/testing/collection_results_harness';

/** Harness for the FleetCollectionClientResults component. */
export class FleetCollectionClientResultsHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-client-results';

  readonly overviewContainer = this.locatorFor('.overview-container');

  readonly downloadButton = this.locatorFor(FlowResultsDownloadButtonHarness);

  readonly collectionResults = this.locatorFor(CollectionResultsHarness);

  async getOverviewText(): Promise<string> {
    const overviewContainer = await this.overviewContainer();
    return overviewContainer.text();
  }
}
