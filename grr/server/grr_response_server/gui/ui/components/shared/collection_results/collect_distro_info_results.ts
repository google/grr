import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CollectDistroInfoResult as ApiCollectDistroInfoResult} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';

function collectDistroInfoResultsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly ApiCollectDistroInfoResult[] {
  return collectionResults.map((res) => {
    return res.payload as ApiCollectDistroInfoResult;
  });
}

/** Component that displays `CollectDistroInfo` flow results. */
@Component({
  selector: 'collect-distro-info-results',
  templateUrl: './collect_distro_info_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectDistroInfoResults {
  collectionResults = input.required<
    readonly ApiCollectDistroInfoResult[],
    readonly CollectionResult[]
  >({
    transform: collectDistroInfoResultsFromCollectionResults,
  });
}
