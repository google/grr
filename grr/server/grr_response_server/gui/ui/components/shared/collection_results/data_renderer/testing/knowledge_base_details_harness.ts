import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the KnowledgeBaseDetails component. */
export class KnowledgeBaseDetailsHarness extends ComponentHarness {
  static hostSelector = 'knowledge-base-details';

  readonly table = this.locatorFor('table');
}
