import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';

import {CollectionResultsHarness} from '../../../shared/collection_results/testing/collection_results_harness';
import {ErrorMessageHarness} from '../../../shared/testing/error_message_harness';

/** Harness for the FlowResults component. */
export class FlowResultsHarness extends ComponentHarness {
  static hostSelector = 'flow-results';

  readonly errorMessage = this.locatorForOptional(ErrorMessageHarness);

  readonly loadMoreButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'Load more'}),
  );

  readonly collectionResults = this.locatorForOptional(
    CollectionResultsHarness,
  );

  async hasLoadMoreButton(): Promise<boolean> {
    return (await this.loadMoreButton()) !== null;
  }
}
