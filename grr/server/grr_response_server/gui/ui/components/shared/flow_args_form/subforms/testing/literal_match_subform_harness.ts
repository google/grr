import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the LiteralMatchSubform component. */
export class LiteralMatchSubformHarness extends ComponentHarness {
  static hostSelector = 'literal-match-subform';

  /** Literal input. */
  readonly literalInput = this.locatorFor(MatInputHarness);
}
