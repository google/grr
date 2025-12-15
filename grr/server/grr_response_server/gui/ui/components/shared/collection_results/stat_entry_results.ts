import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {StatEntry as ApiStatEntry} from '../../../lib/api/api_interfaces';
import {
  isRegistryEntry,
  isStatEntry,
  translateVfsStatEntry,
} from '../../../lib/api/translation/flow';
import {isFlowResult} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../collapsible_container';
import {
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';
import {
  RegistryKeyWithClientId,
  RegistryResultsTable,
  RegistryValueWithClientId,
} from './data_renderer/registry_results_table';

interface TaggedResult {
  readonly tag: string;
  readonly fileResults: FlowFileResult[];
  readonly registryResults: Array<
    RegistryKeyWithClientId | RegistryValueWithClientId
  >;
}

function resultsPerTagFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): Map<string, TaggedResult> {
  const taggedResults = new Map<string, TaggedResult>();

  for (const result of collectionResults) {
    const tag = isFlowResult(result) ? result.tag : '';

    if (!taggedResults.has(tag)) {
      taggedResults.set(tag, {
        tag,
        fileResults: [],
        registryResults: [],
      });
    }
    const taggedResult = taggedResults.get(tag)!;
    const statOrRegistryEntry = translateVfsStatEntry(
      result.payload as ApiStatEntry,
    );
    if (isStatEntry(statOrRegistryEntry)) {
      taggedResult.fileResults.push({
        statEntry: statOrRegistryEntry,
        clientId: result.clientId,
      });
    } else if (isRegistryEntry(statOrRegistryEntry)) {
      taggedResult.registryResults.push({
        ...statOrRegistryEntry,
        clientId: result.clientId,
      });
    }
  }
  return taggedResults;
}

/** Component that displays `StatEntry` flow results. */
@Component({
  selector: 'stat-entry-results',
  templateUrl: './stat_entry_results.ng.html',
  imports: [
    CollapsibleContainer,
    CollapsibleTitle,
    CollapsibleContent,
    CommonModule,
    FileResultsTable,
    RegistryResultsTable,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatEntryResults {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected readonly CollapsibleState = CollapsibleState;

  protected resultsPerTag = computed(() => {
    return resultsPerTagFromCollectionResults(this.collectionResults());
  });

  protected isHuntResult = computed(() => {
    return this.collectionResults().some(isHuntResult);
  });
}
