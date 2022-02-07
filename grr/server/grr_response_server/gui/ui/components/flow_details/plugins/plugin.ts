import {Component, Input, OnDestroy} from '@angular/core';
import {ReplaySubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {getExportedResultsCsvUrl, getExportedResultsSqliteUrl, getExportedResultsYamlUrl, getFlowFilesArchiveUrl} from '../../../lib/api/http_api_service';
import {Flow, FlowState} from '../../../lib/models/flow';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {makeLegacyLink} from '../../../lib/routing';

/** An entry in the Flow's Download/Export menu, e.g. "Download (CSV)". */
export interface ExportMenuItem {
  /** The displayed title of the menu item, e.g. "Download (CSV)". */
  title: string;

  /**
   * If set, instructs the browser to name the downloaded file, e.g.
   * `${clientId}_${flow.flowId}.sql.zip`.
   */
  downloadName?: string;

  /** URL of the file to download. */
  url: string;
}

/**
 * Base class for all flow details plugins.
 */
@Component({template: ''})
export abstract class Plugin implements OnDestroy {
  private flowValue?: Flow;

  /**
   * Subject emitting new Flow values on every "flow"
   * binding change.
   */
  readonly flow$ = new ReplaySubject<Flow>(1);

  readonly fallbackUrl$ = this.flow$.pipe(map(flow => {
    const {flowId, clientId} = flow;
    return makeLegacyLink(`#/clients/${clientId}/flows/${flowId}`);
  }));

  readonly ngOnDestroy = observeOnDestroy(this, () => {
    this.flow$.complete();
  });

  /**
   * Flow input binding containing flow data information to display.
   */
  @Input()
  set flow(value: Flow) {
    this.flowValue = value;
    this.flow$.next(value);
  }

  get flow(): Flow {
    return this.flowValue!;
  }

  /** Returns a menu item triggering downloading the flow's collected files. */
  getDownloadFilesExportMenuItem(flow: Flow): ExportMenuItem {
    const clientId = flow.clientId.replace('.', '_');
    return {
      title: 'Download files',
      url: getFlowFilesArchiveUrl(flow.clientId, flow.flowId),
      downloadName: `${clientId}_${flow.flowId}.zip`,
    };
  }

  /**
   * Returns export/download menu items, linking to download flow results, e.g.
   * "Download (CSV)".
   *
   * The first entry will be shown as a full button, all following entries will
   * be shown in a dropdown menu.
   *
   * Override this function in a child class to control which entries to show.
   * You can fall back to super.getExportMenuItems(flow) and modify any items;
   *
   * If the flow is still running or reports no results in the metadata, no
   * export/download buttons will be shown.
   */
  getExportMenuItems(flow: Flow): ReadonlyArray<ExportMenuItem> {
    const clientId = flow.clientId.replace('.', '_');
    const items: ExportMenuItem[] = [];

    // TODO: There are cases where StatEntries are but no actual
    // file contents are collected. In this case, we shouldn't show this entry.
    if (flow?.resultCounts?.find(rc => rc.type === 'StatEntry' && rc.count)) {
      items.push(this.getDownloadFilesExportMenuItem(flow));
    }

    return [
      ...items,
      {
        title: 'Download (CSV)',
        url: getExportedResultsCsvUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.csv.zip`,
      },
      {
        title: 'Download (YAML)',
        url: getExportedResultsYamlUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.yaml.zip`,
      },
      {
        title: 'Download (SQLite)',
        url: getExportedResultsSqliteUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.sql.zip`,
      },
    ];
  }

  /**
   * Returns a brief description of the amount of results, e.g. "5 files" to be
   * shown in the flow card.
   */
  getResultDescription(flow: Flow): string|undefined {
    if (isNonNull(flow.resultCounts)) {
      const totalCount = flow.resultCounts.reduce(
          (sum, resultCount) => sum + (resultCount.count ?? 0), 0);

      if (totalCount === 0 && flow.state === FlowState.RUNNING) {
        // Hide "0 results" if flow is still running.
        return '';
      } else {
        // As soon as we have ≥1 results, show the result count. Only show
        // "0 results" if the flow is finished.
        return totalCount === 1 ? '1 result' : `${totalCount} results`;
      }
    } else {
      return undefined;
    }
  }
}
