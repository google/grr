import {ComponentHarness} from '@angular/cdk/testing';

import {CodeblockHarness} from '../../testing/codeblock_harness';

/** Harness for the TextView component. */
export class TextViewHarness extends ComponentHarness {
  static hostSelector = 'text-view';

  readonly codeblock = this.locatorFor(CodeblockHarness);
}
