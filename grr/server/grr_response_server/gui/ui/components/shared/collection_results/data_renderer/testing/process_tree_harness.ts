import {ComponentHarness} from '@angular/cdk/testing';
import {MatTreeHarness} from '@angular/material/tree/testing';
import {ErrorMessageHarness} from '../../../testing/error_message_harness';

/** Harness for the ProcessTree component. */
export class ProcessTreeHarness extends ComponentHarness {
  static hostSelector = 'process-tree';

  readonly tree = this.locatorFor(MatTreeHarness);

  readonly errorMessage = this.locatorForOptional(ErrorMessageHarness);
}
