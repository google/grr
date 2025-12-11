import {ComponentHarness} from '@angular/cdk/testing';

import {CodeblockHarness} from '../data_renderer/testing/codeblock_harness';

/** Harness for the ExecuteBinaryResponses component. */
export class ExecuteBinaryResponsesHarness extends ComponentHarness {
  static hostSelector = 'execute-binary-responses';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly codeblocks = this.locatorForAll(CodeblockHarness);
}
