import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CollectDistroInfoResult as ApiCollectDistroInfoResult} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';

/** Component that displays `CollectDistroInfo` flow results. */
@Component({
  selector: 'collect-distro-info-results',
  templateUrl: './collect_distro_info_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectDistroInfoResults {
  collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected collectDistroInfoResultFromCollectionResult(
    collectionResult: CollectionResult,
  ): ApiCollectDistroInfoResult {
    return collectionResult.payload as ApiCollectDistroInfoResult;
  }
}
