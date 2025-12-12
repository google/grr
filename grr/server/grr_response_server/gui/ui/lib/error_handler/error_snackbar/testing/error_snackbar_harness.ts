import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';

/** Harness for the ErrorSnackBar component. */
export class ErrorSnackBarHarness extends ComponentHarness {
  static hostSelector = 'error-snackbar';

  readonly reloadButton = this.locatorFor(
    MatButtonHarness.with({selector: '[aria-label="reload"]'}),
  );

  readonly ignoreButton = this.locatorFor(
    MatButtonHarness.with({selector: '[aria-label="ignore"]'}),
  );

  readonly copyButton = this.locatorFor(
    MatButtonHarness.with({selector: '[aria-label="copy error message"]'}),
  );

  readonly copyIcon = this.locatorForOptional(
    MatIconHarness.with({name: 'content_copy'}),
  );

  readonly copyConfirmation = this.locatorForOptional(
    MatIconHarness.with({name: 'check'}),
  );

  async getText() {
    return (await this.host()).text();
  }
}
