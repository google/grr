import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {KnowledgeBase as KnowledgeBaseModel} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {KnowledgeBaseDetails} from './data_renderer/knowledge_base_details';

function knowledgeBasesFromCollectionResults(
  results: readonly CollectionResult[],
): readonly KnowledgeBaseModel[] {
  return results.map((item) => item.payload as KnowledgeBaseModel);
}

/**
 * Component that shows `KnowledgeBase` flow results.
 */
@Component({
  selector: 'knowledge-bases',
  templateUrl: './knowledge_bases.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, KnowledgeBaseDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgeBases {
  readonly collectionResults = input.required<
    readonly KnowledgeBaseModel[],
    readonly CollectionResult[]
  >({
    transform: knowledgeBasesFromCollectionResults,
  });
}
