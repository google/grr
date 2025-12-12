import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {ExecutePythonHackResult as ApiClientExecutePythonHackResult} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {Codeblock} from './data_renderer/codeblock';

/** Details and results of ExecutePythonHack flow. */
@Component({
  selector: 'execute-python-hack-results',
  templateUrl: './execute_python_hack_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [Codeblock, CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecutePythonHackResults {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected executePythonHackResultFromCollectionResult(
    collectionResult: CollectionResult,
  ): string[] {
    return (
      (
        collectionResult.payload as ApiClientExecutePythonHackResult
      ).resultString?.split('\n') ?? []
    );
  }
}
