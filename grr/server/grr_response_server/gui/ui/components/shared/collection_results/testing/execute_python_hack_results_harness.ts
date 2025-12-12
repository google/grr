import {ComponentHarness} from '@angular/cdk/testing';

import {CodeblockHarness} from '../data_renderer/testing/codeblock_harness';

/** Harness for the ExecutePythonHackResults component. */
export class ExecutePythonHackResultsHarness extends ComponentHarness {
  static hostSelector = 'execute-python-hack-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly codeblocks = this.locatorForAll(CodeblockHarness);
}
