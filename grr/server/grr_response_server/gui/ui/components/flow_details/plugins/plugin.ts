import {Component, Input, OnDestroy} from '@angular/core';
import {ReplaySubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {
  getExportedResultsCommandLink,
  getExportedResultsCsvUrl,
  getExportedResultsSqliteUrl,
  getExportedResultsYamlUrl,
  getFlowFilesArchiveUrl,
} from '../../../lib/api/http_api_service';
import {FlowState, type Flow} from '../../../lib/models/flow';
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

  /** Type of button, e.g. "COPY_TO_CLIPBOARD" or "LINK". */
  type: ButtonType;
}

/** Enum that defines the type of button, e.g. "COPY_TO_CLIPBOARD" or "LINK". */
export enum ButtonType {
  COPY_TO_CLIPBOARD = 0,
  LINK = 1,
}

/**
 * Base class for all flow details plugins.
 */
@Component({standalone: false, template: ''})
export abstract class Plugin implements OnDestroy {
  private flowValue?: Flow;
  exportCommandPrefixValue?: string;

  /**
   * Subject emitting new Flow values on every "flow"
   * binding change.
   */
  readonly flow$ = new ReplaySubject<Flow>(1);

  readonly exportCommandPrefix$ = new ReplaySubject<string>(1);

  readonly fallbackUrl$ = this.flow$.pipe(
    map((flow) => {
      const {flowId, clientId} = flow;
      return makeLegacyLink(`#/clients/${clientId}/flows/${flowId}`);
    }),
  );

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

  @Input()
  set exportCommandPrefix(value: string) {
    this.exportCommandPrefixValue = value;
    this.exportCommandPrefix$.next(value);
  }

  get exportCommandPrefix(): string {
    return this.exportCommandPrefixValue!;
  }

  /** Returns a menu item triggering downloading the flow's collected files. */
  getDownloadFilesExportMenuItem(flow: Flow): ExportMenuItem {
    const clientId = flow.clientId.replace('.', '_');
    return {
      title: 'Download files',
      url: getFlowFilesArchiveUrl(flow.clientId, flow.flowId),
      downloadName: `${clientId}_${flow.flowId}.zip`,
      type: ButtonType.LINK,
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
   * You can fall back to super.getExportMenuItems(flow, exportCommandPrefix)
   * and modify any items;
   *
   * If the flow is still running or reports no results in the metadata, no
   * export/download buttons will be shown.
   */
  getExportMenuItems(
    flow: Flow,
    exportCommandPrefix: string,
  ): readonly ExportMenuItem[] {
    const clientId = flow.clientId.replace('.', '_');
    const items: ExportMenuItem[] = [];

    // TODO: There are cases where StatEntries are but no actual
    // file contents are collected. In this case, we shouldn't show this entry.
    if (flow?.resultCounts?.find((rc) => rc.type === 'StatEntry' && rc.count)) {
      items.push(this.getDownloadFilesExportMenuItem(flow));
    }

    items.push(
      {
        title: 'Download (CSV)',
        url: getExportedResultsCsvUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.csv.zip`,
        type: ButtonType.LINK,
      },
      {
        title: 'Download (YAML)',
        url: getExportedResultsYamlUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.yaml.zip`,
        type: ButtonType.LINK,
      },
      {
        title: 'Download (SQLite)',
        url: getExportedResultsSqliteUrl(flow.clientId, flow.flowId),
        downloadName: `${clientId}_${flow.flowId}.sql.zip`,
        type: ButtonType.LINK,
      },
    );

    if (exportCommandPrefix && exportCommandPrefix !== '') {
      items.push({
        title: 'Download (Print CLI)',
        url: getExportedResultsCommandLink(
          exportCommandPrefix,
          flow.clientId,
          `${clientId}_${flow.flowId}.zip`,
          flow.flowId,
        ),
        downloadName: `CLI Export Command`,
        type: ButtonType.COPY_TO_CLIPBOARD,
      });
    }

    return items;
  }

  /**
   * Returns a brief description of the amount of results, e.g. "5 files" to be
   * shown in the flow card.
   */
  getResultDescription(flow: Flow): string | undefined {
    if (isNonNull(flow.resultCounts)) {
      const totalCount = flow.resultCounts.reduce(
        (sum, resultCount) => sum + (resultCount.count ?? 0),
        0,
      );

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
