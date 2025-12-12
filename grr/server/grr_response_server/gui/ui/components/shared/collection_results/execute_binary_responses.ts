import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {ExecuteBinaryResponse as ApiExecuteBinaryResponse} from '../../../lib/api/api_interfaces';
import {translateExecuteBinaryResponse} from '../../../lib/api/translation/flow';
import {ExecuteBinaryResponse} from '../../../lib/models/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {Codeblock} from './data_renderer/codeblock';

/** Details and results of LaunchBinary flow. */
@Component({
  selector: 'execute-binary-responses',
  templateUrl: './execute_binary_responses.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [Codeblock, CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecuteBinaryResponses {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected executeBinaryResponseFromCollectionResult(
    collectionResult: CollectionResult,
  ): ExecuteBinaryResponse {
    return translateExecuteBinaryResponse(
      collectionResult.payload as ApiExecuteBinaryResponse,
    );
  }
}
