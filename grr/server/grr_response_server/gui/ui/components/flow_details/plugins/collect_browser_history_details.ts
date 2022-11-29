import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry} from '../../../components/flow_details/helpers/file_results_table';
import {Browser, BrowserProgress, BrowserProgressStatus, CollectBrowserHistoryArgs, CollectBrowserHistoryProgress, CollectBrowserHistoryResult} from '../../../lib/api/api_interfaces';
import {translateStatEntry} from '../../../lib/api_translation/flow';
import {Flow, FlowResult, FlowState} from '../../../lib/models/flow';
import {assertNonNull} from '../../../lib/preconditions';
import {FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';
import {Status as ResultAccordionStatus} from '../helpers/result_accordion';

import {ExportMenuItem, Plugin} from './plugin';


declare interface BrowserRow {
  name: Browser;
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

    if (progress.status === BrowserProgressStatus.SUCCESS) {
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
    } else if (
        progress.status === BrowserProgressStatus.ERROR ||
        flow.state === FlowState.ERROR) {
      status = ResultAccordionStatus.ERROR;
      description = progress.description ?? '';
    } else if (
        progress.status === BrowserProgressStatus.IN_PROGRESS &&
        flow.state === FlowState.RUNNING) {
      status = ResultAccordionStatus.IN_PROGRESS;
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

  override getExportMenuItems(flow: Flow): ReadonlyArray<ExportMenuItem> {
    const items = super.getExportMenuItems(flow);
    const downloadItem = this.getDownloadFilesExportMenuItem(flow);

    if (flow.resultCounts?.find(
            rc => rc.type === 'CollectBrowserHistoryResult' && rc.count) &&
        !items.find(item => item.url === downloadItem.url)) {
      return [downloadItem, ...items];
    } else {
      return items;
    }
  }
}

function mapFlowResults(results?: ReadonlyArray<FlowResult>):
    ReadonlyArray<FlowFileResult>|undefined {
  return results?.map(
      r => flowFileResultFromStatEntry(translateStatEntry(
          (r.payload as CollectBrowserHistoryResult).statEntry!)));
}
