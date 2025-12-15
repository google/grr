import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {KnowledgeBase as KnowledgeBaseModel} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {KnowledgeBaseDetails} from './data_renderer/knowledge_base_details';

/**
 * Component that shows `KnowledgeBase` flow results.
 */
@Component({
  selector: 'knowledge-bases',
  templateUrl: './knowledge_bases.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, CopyButton, KnowledgeBaseDetails],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgeBases {
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected knowledgeBaseFromCollectionResult(
    result: CollectionResult,
  ): KnowledgeBaseModel {
    return result.payload as KnowledgeBaseModel;
  }
}
