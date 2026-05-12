import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the RegexMatchSubform component. */
export class RegexMatchSubformHarness extends ComponentHarness {
  static hostSelector = 'regex-match-subform';

  /** Regex input. */
  readonly regexInput = this.locatorFor(
    MatInputHarness.with({selector: '[name="regex"]'}),
  );

  /** Length input. */
  readonly lengthInput = this.locatorFor(
    MatInputHarness.with({selector: '[name="length"]'}),
  );
}
