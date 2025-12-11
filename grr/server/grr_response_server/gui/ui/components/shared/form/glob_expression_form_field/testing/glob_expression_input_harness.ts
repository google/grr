import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the GlobExpressionInput component. */
export class GlobExpressionInputHarness extends ComponentHarness {
  static hostSelector = 'glob-expression-input';

  /** Input field for the glob expression. */
  readonly input = this.locatorFor(MatInputHarness);
}
