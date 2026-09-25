import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {Process} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {ProcessTree} from './data_renderer/process_tree';

function processesFromCollectionResults(
  results: readonly CollectionResult[],
): readonly Process[] {
  const processes: Process[] = results.map((item) => item.payload as Process);
  const missingPids = processes.filter((process) => process.pid === undefined);
  if (missingPids.length > 0) {
    throw new Error(
      `Expected Process with pid, received ${missingPids.length} results without pid.`,
    );
  }
  return processes;
}

/**
 * Component that displays ListProcesses flow results.
 */
@Component({
  selector: 'processes',
  templateUrl: './processes.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, ProcessTree],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Processes {
  readonly collectionResults = input.required<
    readonly Process[],
    readonly CollectionResult[]
  >({
    transform: processesFromCollectionResults,
  });
}
