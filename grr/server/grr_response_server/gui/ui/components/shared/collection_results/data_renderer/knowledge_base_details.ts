import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {KnowledgeBase as KnowledgeBaseModel} from '../../../../lib/api/api_interfaces';
import {CopyButton} from '../../copy_button';

/**
 * Component displaying the knowledge base of a Client.
 */
@Component({
  selector: 'knowledge-base-details',
  templateUrl: './knowledge_base_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgeBaseDetails {
  readonly knowledgeBase = input.required<KnowledgeBaseModel | undefined>();
}
