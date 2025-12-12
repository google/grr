import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {ExecuteResponse as ApiExecuteResponse} from '../../../lib/api/api_interfaces';
import {translateExecuteResponse} from '../../../lib/api/translation/flow';
import {ExecuteResponse} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';

/** Component that displays `ExecuteResponse` flow results. */
@Component({
  selector: 'execute-response-results',
  templateUrl: './execute_response_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecuteResponseResults {
  collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected executeResponseResultFromCollectionResult(
    collectionResult: CollectionResult,
  ): ExecuteResponse {
    return translateExecuteResponse(
      collectionResult.payload as ApiExecuteResponse,
    );
  }
}
