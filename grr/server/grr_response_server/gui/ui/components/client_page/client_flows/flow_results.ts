import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input as routerInput,
  signal,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {Title} from '@angular/platform-browser';

import {Flow, FlowType} from '../../../lib/models/flow';
import {ClientStore, FlowResultsQuery} from '../../../store/client_store';
import {CollectionResults} from '../../shared/collection_results/collection_results';
import {FlowResultsDownloadButton} from '../../shared/collection_results/flow_results_download_button/flow_results_download_button';
import {ErrorMessage} from '../../shared/error_message';

/** Default offset for fetching flow results. */
const DEFAULT_FLOW_RESULT_OFFSET = 0;
/** Default number of results to fetch. */
const DEFAULT_FLOW_RESULT_COUNT = 500;

/**
 * Component displaying results of a single flow.
 */
@Component({
  selector: 'flow-results',
  templateUrl: './flow_results.ng.html',
  styleUrls: ['./flow_results.scss'],
  imports: [
    CommonModule,
    CollectionResults,
    ErrorMessage,
    FlowResultsDownloadButton,
    MatIconModule,
    MatButtonModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowResults {
  protected readonly clientStore = inject(ClientStore);

  private readonly resultsOffset = signal(DEFAULT_FLOW_RESULT_OFFSET);
  private readonly resultsCount = signal(DEFAULT_FLOW_RESULT_COUNT);
  private readonly resultsTag = signal('');
  private readonly resultsType = signal('');

  flowId = routerInput<string | undefined>();
  protected readonly FlowType = FlowType;

  flow = computed<Flow | undefined>(() => {
    const flowId = this.flowId();
    if (flowId) {
      return this.clientStore.flowsByFlowId().get(flowId);
    }
    return undefined;
  });

  constructor() {
    inject(Title).setTitle('GRR | Client > Flow > Results');

    this.clientStore.pollFlowResults(
      computed<FlowResultsQuery>(() => {
        return {
          flowId: this.flowId(),
          offset: this.resultsOffset(),
          count: this.resultsCount(),
          withTag: this.resultsTag(),
          withType: this.resultsType(),
        };
      }),
    );
  }

  loadMore(count = 500) {
    this.resultsCount.set(this.resultsCount() + count);
  }

  loadTaggedResults(tag: string, type: string) {
    this.resultsTag.set(tag);
    this.resultsType.set(type);
  }
}
