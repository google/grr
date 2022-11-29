import {Clipboard} from '@angular/cdk/clipboard';
import {Component, Inject, InjectionToken} from '@angular/core';
import {MAT_SNACK_BAR_DATA} from '@angular/material/snack-bar';

/** InjectionToken to allow mocking the browser window in tests. */
export const WINDOW = new InjectionToken<Window>('Window');

/** Snackbar that shows and allows copying an error message. */
@Component({
  selector: 'app-error-snackbar',
  templateUrl: './error_snackbar.ng.html',
  styleUrls: ['./error_snackbar.scss']
})
export class ErrorSnackBar {
  copied = false;

  constructor(
      private readonly clipboard: Clipboard,
      @Inject(MAT_SNACK_BAR_DATA) readonly error: string,
      @Inject(WINDOW) private readonly window: Window,
  ) {}

  dismiss() {
    // The ErrorSnackBar is shown as last resort when unexpected errors occur.
    // Many Observables do not have a well-defined state after throwing an
    // error, e.g. they might complete and no longer be subscribed to. For now,
    // prevent users from using GRR in this undefined state and nudge them to
    // reload the web app to start from a clean slate.
    this.window.location.reload();
  }

  copy() {
    this.copied = this.clipboard.copy(this.error);
  }
}
