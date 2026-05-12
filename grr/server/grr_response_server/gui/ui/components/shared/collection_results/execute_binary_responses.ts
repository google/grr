import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {ExecuteBinaryResponse as ApiExecuteBinaryResponse} from '../../../lib/api/api_interfaces';
import {translateExecuteBinaryResponse} from '../../../lib/api/translation/flow';
import {ExecuteBinaryResponse} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';
import {Codeblock} from './data_renderer/codeblock';

function executeBinaryResponseFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ExecuteBinaryResponse[] {
  return collectionResults
    .map((res) => {
      return (res.payload as ApiExecuteBinaryResponse) ?? {};
    })
    .map(translateExecuteBinaryResponse);
}

/** Details and results of LaunchBinary flow. */
@Component({
  selector: 'execute-binary-responses',
  templateUrl: './execute_binary_responses.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [Codeblock, CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecuteBinaryResponses {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    readonly ExecuteBinaryResponse[],
    readonly CollectionResult[]
  >({
    transform: executeBinaryResponseFromCollectionResults,
  });
}
