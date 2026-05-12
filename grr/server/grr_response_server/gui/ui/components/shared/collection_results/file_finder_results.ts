import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {FileFinderResult} from '../../../lib/api/api_interfaces';
import {
  isRegistryEntry,
  isStatEntry,
  translateHashToHex,
  translateVfsStatEntry,
} from '../../../lib/api/translation/flow';
import {RegistryKey, RegistryValue} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';
import {
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';
import {RegistryResultsTable} from './data_renderer/registry_results_table';

interface FileOrRegistryResult {
  readonly fileResult?: FlowFileResult;
  readonly registryResult?: RegistryKey | RegistryValue;
}

function flowFileOrRegistryResultsFromCollectionResults(
  results: readonly CollectionResult[],
): readonly FileOrRegistryResult[] {
  return results.map((item) => {
    const payload = item.payload as FileFinderResult;
    if (!payload.statEntry) {
      return {} as FileOrRegistryResult;
    }

    const statOrRegistryEntry = translateVfsStatEntry(payload.statEntry);
    if (isStatEntry(statOrRegistryEntry)) {
      const fileResult: FlowFileResult = {
        statEntry: statOrRegistryEntry,
        hashes: translateHashToHex(payload.hashEntry ?? {}),
        clientId: item.clientId,
      };
      return {fileResult};
    } else if (isRegistryEntry(statOrRegistryEntry)) {
      const registryResult: RegistryKey | RegistryValue = {
        ...statOrRegistryEntry,
      };
      return {registryResult};
    }
    return {} as FileOrRegistryResult;
  });
}

/**
 * Component that shows `FileFinderResult` flow results.
 */
@Component({
  selector: 'file-finder-results',
  templateUrl: './file_finder_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, FileResultsTable, RegistryResultsTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileFinderResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected readonly fileOrRegistryResults = computed(() => {
    return flowFileOrRegistryResultsFromCollectionResults(
      this.collectionResults(),
    );
  });

  protected readonly registryResults = computed(() => {
    return this.fileOrRegistryResults()
      .filter((item) => item.registryResult !== undefined)
      .map((item) => item.registryResult!);
  });

  protected readonly fileResults = computed(() => {
    return this.fileOrRegistryResults()
      .filter((item) => item.fileResult !== undefined)
      .map((item) => item.fileResult!);
  });
}
