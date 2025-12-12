import {Clipboard} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';

import {
  CollectLargeFileFlowArgs,
  FileFinderActionAction,
  FileFinderArgs,
  OsqueryFlowArgs,
  OsqueryProgress,
  ReadLowLevelArgs,
} from '../../../../lib/api/api_interfaces';
import {
  getExportedResultsCommandLink,
  getExportedResultsCsvUrl,
  getExportedResultsSqliteUrl,
  getExportedResultsYamlUrl,
  getFlowFilesArchiveUrl,
  getTempBlobUrl,
  getTimelineBodyFileUrl,
} from '../../../../lib/api/http_api_service';
import {Flow, FlowState, FlowType} from '../../../../lib/models/flow';
import {checkExhaustive} from '../../../../lib/utils';
import {GlobalStore} from '../../../../store/global_store';

/** An entry in the Flow's Download/Export menu. */
interface ExportMenuItem {
  // The displayed title of the menu item.
  title: string;
  // URL of the file to download.
  url: string;
  // If true, the menu item is a link, otherwise it is a string to copy.
  isLink: boolean;
}

function downloadFilesMenuItem(flow: Flow): ExportMenuItem {
  return {
    title: 'Download files',
    url: getFlowFilesArchiveUrl(flow.clientId, flow.flowId),
    isLink: true,
  };
}

function csvExportMenuItem(flow: Flow): ExportMenuItem {
  return {
    title: 'Download CSV',
    url: getExportedResultsCsvUrl(flow.clientId, flow.flowId),
    isLink: true,
  };
}

function yamlExportMenuItem(flow: Flow): ExportMenuItem {
  return {
    title: 'Download YAML',
    url: getExportedResultsYamlUrl(flow.clientId, flow.flowId),
    isLink: true,
  };
}

function sqliteExportMenuItem(flow: Flow): ExportMenuItem {
  return {
    title: 'Download SQLite',
    url: getExportedResultsSqliteUrl(flow.clientId, flow.flowId),
    isLink: true,
  };
}

function cliExportMenuItem(
  exportCommandPrefix: string,
  flow: Flow,
): ExportMenuItem {
  return {
    title: 'Copy CLI Command',
    url: getExportedResultsCommandLink(
      exportCommandPrefix,
      flow.clientId,
      `${flow.clientId}_${flow.flowId}.zip`,
      flow.flowId,
    ),
    isLink: false,
  };
}

/**
 * Component displaying download button for flow results.
 */
@Component({
  selector: 'flow-results-download-button',
  templateUrl: './flow_results_download_button.ng.html',
  imports: [CommonModule, MatButtonModule, MatIconModule, MatMenuModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowResultsDownloadButton {
  protected readonly globalStore = inject(GlobalStore);
  protected readonly clipboard = inject(Clipboard);

  protected readonly flow = input.required<Flow | undefined>();

  copyToClipboard(str: string) {
    if (str !== null) {
      this.clipboard.copy(str);
    }
  }

  protected exportMenuItems = computed<readonly ExportMenuItem[]>(() => {
    const flow = this.flow();
    if (
      !flow ||
      flow.state !== FlowState.FINISHED ||
      flow.resultCounts?.every((rc) => rc.count === 0) ||
      flow.flowType === undefined
    ) {
      return [];
    }
    const baseExportMenuItems: ExportMenuItem[] = [];
    baseExportMenuItems.push(
      csvExportMenuItem(flow),
      yamlExportMenuItem(flow),
      sqliteExportMenuItem(flow),
    );
    const exportCommandPrefix = this.globalStore.exportCommandPrefix();
    if (exportCommandPrefix) {
      baseExportMenuItems.push(cliExportMenuItem(exportCommandPrefix, flow));
    }

    const items: ExportMenuItem[] = [];

    switch (flow.flowType) {
      case FlowType.OS_QUERY_FLOW:
        const osqueryFlowargs = flow.args as OsqueryFlowArgs;
        const osqueryProgress = flow.progress as OsqueryProgress | undefined;
        if (
          osqueryProgress?.totalRowCount &&
          (osqueryFlowargs.fileCollectionColumns ?? []).length > 0
        ) {
          items.push(downloadFilesMenuItem(flow));
        }
        items.push(...baseExportMenuItems);
        return items;
      case FlowType.COLLECT_BROWSER_HISTORY:
        if (
          flow.resultCounts?.find(
            (rc) => rc.type === 'CollectBrowserHistoryResult' && rc.count,
          )
        ) {
          items.push(downloadFilesMenuItem(flow));
        }
        items.push(...baseExportMenuItems);
        return items;
      case FlowType.FILE_FINDER:
        const fileFinderArgs = flow.args as FileFinderArgs;
        if (
          fileFinderArgs.action?.actionType === FileFinderActionAction.DOWNLOAD
        ) {
          items.push(downloadFilesMenuItem(flow));
        }
        items.push(...baseExportMenuItems);
        return items;
      case FlowType.READ_LOW_LEVEL:
        const lowLevelArgs = flow.args as ReadLowLevelArgs;
        const alphanumericOnly =
          lowLevelArgs?.path?.replace(/[^\p{L}\s]/gu, '') ?? '';
        const archiveFileName = `${flow.clientId}_${flow.flowId}_${alphanumericOnly}`;
        items.push({
          title: 'Download data',
          url: getTempBlobUrl(flow.clientId, archiveFileName),
          isLink: true,
        });
        items.push(...baseExportMenuItems);
        return items;
      case FlowType.TIMELINE_FLOW:
        items.push(
          {
            title: 'Download body file',
            url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
              timestampSubsecondPrecision: true,
              inodeNtfsFileReferenceFormat: false,
              backslashEscape: true,
              carriageReturnEscape: true,
              nonPrintableEscape: true,
            }),
            isLink: true,
          },
          {
            title: 'Download body file (Windows format)',
            url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
              timestampSubsecondPrecision: true,
              inodeNtfsFileReferenceFormat: true,
              backslashEscape: true,
              carriageReturnEscape: true,
              nonPrintableEscape: true,
            }),
            isLink: false,
          },
        );
        return items;
      case FlowType.COLLECT_LARGE_FILE_FLOW:
        const signedUrl = (flow.args as CollectLargeFileFlowArgs).signedUrl;
        if (signedUrl && signedUrl !== '') {
          items.push({
            title: 'Download encrypted file',
            url: signedUrl,
            isLink: true,
          });
        }
        return items;
      case FlowType.COLLECT_FILES_BY_KNOWN_PATH:
      case FlowType.COLLECT_MULTIPLE_FILES:
      case FlowType.STAT_MULTIPLE_FILES:
      case FlowType.HASH_MULTIPLE_FILES:
        items.push(downloadFilesMenuItem(flow));
        items.push(...baseExportMenuItems);
        return items;
      case FlowType.ARTIFACT_COLLECTOR_FLOW:
      case FlowType.CLIENT_FILE_FINDER:
      case FlowType.CLIENT_REGISTRY_FINDER:
      case FlowType.COLLECT_CLOUD_VM_METADATA:
      case FlowType.COLLECT_DISTRO_INFO:
      case FlowType.COLLECT_HARDWARE_INFO:
      case FlowType.COLLECT_INSTALLED_SOFTWARE:
      case FlowType.DELETE_GRR_TEMP_FILES:
      case FlowType.DUMP_PROCESS_MEMORY:
      case FlowType.EXECUTE_PYTHON_HACK:
      case FlowType.GET_CROWDSTRIKE_AGENT_ID:
      case FlowType.GET_MBR:
      case FlowType.GET_MEMORY_SIZE:
      case FlowType.INTERROGATE:
      case FlowType.KILL:
      case FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW:
      case FlowType.LAUNCH_BINARY:
      case FlowType.LIST_CONTAINERS:
      case FlowType.LIST_DIRECTORY:
      case FlowType.LIST_NAMED_PIPES_FLOW:
      case FlowType.LIST_PROCESSES:
      case FlowType.LIST_RUNNING_SERVICES:
      case FlowType.LIST_VOLUME_SHADOW_COPIES:
      case FlowType.MULTI_GET_FILE:
      case FlowType.NETSTAT:
      case FlowType.ONLINE_NOTIFICATION:
      case FlowType.RECURSIVE_LIST_DIRECTORY:
      case FlowType.REGISTRY_FINDER:
      case FlowType.UPDATE_CLIENT:
      case FlowType.YARA_PROCESS_SCAN:
        // TODO: There are cases where StatEntries are but no
        // actual file contents are collected. In this case, we shouldn't show
        // this entry.
        const resultCounts = flow.resultCounts ?? [];
        if (resultCounts.find((rc) => rc.type === 'StatEntry' && rc.count)) {
          items.push(downloadFilesMenuItem(flow));
        }
        items.push(...baseExportMenuItems);
        return items;
      default:
        return checkExhaustive(flow.flowType);
    }
  });
}
