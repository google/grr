import {ComponentHarness} from '@angular/cdk/testing';

import {KnowledgeBaseDetailsHarness} from '../data_renderer/testing/knowledge_base_details_harness';

/** Harness for the KnowledgeBases component. */
export class KnowledgeBasesHarness extends ComponentHarness {
  static hostSelector = 'knowledge-bases';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly knowledgeBaseDetailsHarnesses = this.locatorForAll(
    KnowledgeBaseDetailsHarness,
  );
}
