import {Type} from '@angular/core';

import {getExportedResultsCsvUrl, getExportedResultsSqliteUrl, getExportedResultsYamlUrl, getFlowFilesArchiveUrl} from '../api/http_api_service';
import {Flow, FlowResultCount, FlowState, PaginatedResultView, PreloadedResultView} from '../models/flow';
import {isNonNull} from '../preconditions';
import {makeLegacyLink} from '../routing';

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

/** Rendering a group of flow results (e.g. by type/tag) in a component. */
export interface FlowResultViewSection {
  readonly title: string;
  readonly component:
      Type<PreloadedResultView<unknown>|PaginatedResultView<unknown>>;
  // Flow result section definitions provide a query with tag and/or type. As
  // an example, the flow adapter can choose to display all flow results of one
  // type in a view (e.g. all StatEntries), all results with one tag in one view
  // (e.g. all results of a specific artifact) or mix-and-match.
  readonly query: {readonly type?: string, readonly tag?: string;};
}

/** Providing a link to view details about flow results. */
export interface FlowResultLinkSection {
  readonly title: string;
  readonly routerLink: {}|string;
}

/** A section of flow results that can be rendered with a view or as a link. */
export type FlowResultSection = FlowResultViewSection|FlowResultLinkSection;

/**
 * An adapter describing how to render results, export menu items, and further
 * details of a flow.
 */
export class FlowDetailsAdapter<F extends Flow = Flow> {
  //  TODO: Provide result type based views (e.g. tables) as
  //  fallback.
  getResultViews(flow: F): readonly FlowResultSection[] {
    if (!flow.resultCounts) {
      return [{
        title: 'View legacy flow in the old UI',
        routerLink:
            makeLegacyLink(`#/clients/${flow.clientId}/flows/${flow.flowId}`)
      }];
    }

    // TODO: Deduplicate views with same tag, type, component.
    return flow.resultCounts.map((rc) => this.getResultView(rc, flow.args))
        .filter(isNonNull);
  }

  /**
   * Returns a FlowResultSection for a group of flow results with the same tag
   * and type.
   */
  getResultView(resultGroup: FlowResultCount, args: F['args']):
      FlowResultSection|undefined {
    return;
  }

  /** Returns a menu item triggering downloading the flow's collected files. */
  getDownloadFilesExportMenuItem(flow: F): ExportMenuItem {
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
  getExportMenuItems(flow: F): readonly ExportMenuItem[] {
    const clientId = flow.clientId.replace('.', '_');
    const items: ExportMenuItem[] = [];

    // TODO: There are cases where StatEntries are but no actual
    // file contents are collected. In this case, we shouldn't show this entry.
    if (flow.resultCounts?.find(rc => rc.type === 'StatEntry' && rc.count)) {
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
  getResultDescription(flow: F): string|undefined {
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
