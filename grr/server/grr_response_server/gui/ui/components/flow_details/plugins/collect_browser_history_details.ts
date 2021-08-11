import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FlowFileResult, flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {BrowserProgress, BrowserProgressStatus, CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser, CollectBrowserHistoryProgress, CollectBrowserHistoryResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {Flow, FlowResult, FlowState} from '@app/lib/models/flow';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {translateStatEntry} from '../../../lib/api_translation/flow';
import {assertNonNull} from '../../../lib/preconditions';
import {FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';
import {Status as ResultAccordionStatus} from '../helpers/result_accordion';

import {Plugin} from './plugin';


declare interface BrowserRow {
  name: CollectBrowserHistoryArgsBrowser;
  friendlyName: string;
  progress: BrowserProgress;
  status?: ResultAccordionStatus;
  description: string;
  resultQuery:
      FlowResultsQueryWithAdapter<ReadonlyArray<FlowFileResult>|undefined>;
}



/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'collect-browser-history-details',
  templateUrl: './collect_browser_history_details.ng.html',
  styleUrls: ['./collect_browser_history_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryDetails extends Plugin {
  readonly INITIAL_COUNT = 100;
  readonly LOAD_STEP = 100;

  readonly FINISHED = FlowState.FINISHED;

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  trackByRowName(index: number, item: BrowserRow) {
    return item.name;
  }

  hasProgress$: Observable<boolean> = this.flow$.pipe(
      map((flow) => flow.progress !== undefined),
  );

  args$: Observable<CollectBrowserHistoryArgs> = this.flow$.pipe(
      map((flow) => flow.args as CollectBrowserHistoryArgs),
  );

  flowState$: Observable<FlowState> = this.flow$.pipe(
      map((flow) => flow.state),
  );

  totalFiles$: Observable<number> = this.flow$.pipe(map((flow) => {
    const p = flow.progress as CollectBrowserHistoryProgress;
    return (p.browsers ?? [])
        .reduce((total, cur) => total + (cur.numCollectedFiles ?? 0), 0);
  }));

  browserRows$: Observable<BrowserRow[]> = this.flow$.pipe(map((flow) => {
    const p = flow.progress as CollectBrowserHistoryProgress;
    return (p.browsers ?? []).map(bp => this.createBrowserRow(flow, bp));
  }));

  archiveUrl$: Observable<string> = this.flow$.pipe(map((flow) => {
    return this.httpApiService.getFlowFilesArchiveUrl(
        flow.clientId, flow.flowId);
  }));

  archiveFileName$: Observable<string> = this.flow$.pipe(map((flow) => {
    return flow.clientId.replace('.', '_') + '_' + flow.flowId + '.zip';
  }));

  private capitalize(v: string): string {
    return v[0].toUpperCase() + v.slice(1);
  }

  private createBrowserRow(flow: Flow, progress: BrowserProgress): BrowserRow {
    assertNonNull(progress.browser, 'progress.browser');

    const friendlyName = progress.browser.toLowerCase()
                             .split('_')
                             .map(this.capitalize)
                             .join(' ');


    let status = ResultAccordionStatus.NONE;
    let description = '';

    if (progress.status === BrowserProgressStatus.ERROR) {
      status = ResultAccordionStatus.ERROR;
      description = progress.description ?? '';
    } else if (progress.status === BrowserProgressStatus.IN_PROGRESS) {
      status = ResultAccordionStatus.IN_PROGRESS;
    } else if (progress.status === BrowserProgressStatus.SUCCESS) {
      if (!progress.numCollectedFiles) {
        status = ResultAccordionStatus.WARNING;
        description = 'No files collected';
      } else if (progress.numCollectedFiles === 1) {
        status = ResultAccordionStatus.SUCCESS;
        description = '1 file';
      } else {
        status = ResultAccordionStatus.SUCCESS;
        description = `${progress.numCollectedFiles} files`;
      }
    }

    return {
      name: progress.browser,
      friendlyName,
      progress,
      status,
      description,
      resultQuery: {
        flow,
        withTag: progress.browser.toUpperCase(),
        resultMapper: mapFlowResults,
      },
    };
  }
}

function mapFlowResults(results?: ReadonlyArray<FlowResult>):
    ReadonlyArray<FlowFileResult>|undefined {
  return results?.map(
      r => flowFileResultFromStatEntry(translateStatEntry(
          (r.payload as CollectBrowserHistoryResult).statEntry!)));
}
