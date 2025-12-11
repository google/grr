import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';

import {Process} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {ProcessTree} from './data_renderer/process_tree';

function processesPerClientIdFromCollectionResults(
  results: readonly CollectionResult[],
): Map<string, Process[]> {
  const processesPerClientId = new Map<string, Process[]>();
  const missingPids: Process[] = [];

  for (const item of results) {
    const process = item.payload as Process;
    if (process.pid === undefined) {
      missingPids.push(process);
      continue;
    }
    if (!processesPerClientId.has(item.clientId)) {
      processesPerClientId.set(item.clientId, []);
    }
    processesPerClientId.get(item.clientId)!.push(process);
  }
  if (missingPids.length > 0) {
    // TODO: This should be a warning and show other process trees
    throw new Error(
      `Expected Process with pid, received ${missingPids.length} results without pid.`,
    );
  }
  return processesPerClientId;
}

/**
 * Component that displays ListProcesses flow results.
 */
@Component({
  selector: 'processes',
  templateUrl: './processes.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton, ProcessTree],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Processes {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = computed(() => {
    return this.collectionResults().some(isHuntResult);
  });

  protected processesPerClientId = computed(() => {
    return processesPerClientIdFromCollectionResults(this.collectionResults());
  });
}
