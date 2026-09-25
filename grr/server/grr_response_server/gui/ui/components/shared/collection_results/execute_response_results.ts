import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {ExecuteResponse as ApiExecuteResponse} from '../../../lib/api/api_interfaces';
import {translateExecuteResponse} from '../../../lib/api/translation/flow';
import {ExecuteResponse} from '../../../lib/models/flow';
import {CollectionResult} from '../../../lib/models/result';

function executeResponseResultsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ExecuteResponse[] {
  return collectionResults.map((res) => {
    return translateExecuteResponse(res.payload as ApiExecuteResponse);
  });
}

/** Component that displays `ExecuteResponse` flow results. */
@Component({
  selector: 'execute-response-results',
  templateUrl: './execute_response_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecuteResponseResults {
  collectionResults = input.required<
    readonly ExecuteResponse[],
    readonly CollectionResult[]
  >({
    transform: executeResponseResultsFromCollectionResults,
  });
}
