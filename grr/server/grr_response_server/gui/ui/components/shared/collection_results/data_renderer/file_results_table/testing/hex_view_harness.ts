import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the HexView component. */
export class HexViewHarness extends ComponentHarness {
  static hostSelector = 'hex-view';

  readonly hexTable = this.locatorFor('.hex-table');
  readonly charsTable = this.locatorFor('.chars-table');
}
