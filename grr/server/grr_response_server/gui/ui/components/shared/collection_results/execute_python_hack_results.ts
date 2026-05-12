import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {ExecutePythonHackResult as ApiClientExecutePythonHackResult} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {Codeblock} from './data_renderer/codeblock';

function executePythonHackResultFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): ReadonlyArray<string[]> {
  return collectionResults.map((res) => {
    return (
      (res.payload as ApiClientExecutePythonHackResult).resultString?.split(
        '\n',
      ) ?? []
    );
  });
}

/** Details and results of ExecutePythonHack flow. */
@Component({
  selector: 'execute-python-hack-results',
  templateUrl: './execute_python_hack_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [Codeblock, CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecutePythonHackResults {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    ReadonlyArray<string[]>,
    readonly CollectionResult[]
  >({
    transform: executePythonHackResultFromCollectionResults,
  });
}
