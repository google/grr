import {Clipboard} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  InjectionToken,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {
  MAT_SNACK_BAR_DATA,
  MatSnackBarModule,
  MatSnackBarRef,
} from '@angular/material/snack-bar';

/** InjectionToken to allow mocking the browser window in tests. */
export const WINDOW = new InjectionToken<Window>('Window');

/** Snackbar that shows and allows copying an error message. */
@Component({
  selector: 'error-snackbar',
  templateUrl: './error_snackbar.ng.html',
  styleUrls: ['./error_snackbar.scss'],
  imports: [CommonModule, MatButtonModule, MatIconModule, MatSnackBarModule],
  providers: [
    {
      provide: WINDOW,
      useValue: window,
    },
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ErrorSnackBar {
  private readonly snackBarRef = inject(MatSnackBarRef);
  private readonly window = inject(WINDOW);
  private readonly clipboard = inject(Clipboard);

  protected readonly error = inject(MAT_SNACK_BAR_DATA);

  protected copied = false;

  reload() {
    // The ErrorSnackBar is shown as last resort when unexpected errors occur.
    // This is the recommended way, as the page might miss information.
    this.window.location.reload();
  }

  ignore() {
    // The ErrorSnackBar is shown as last resort when unexpected errors occur.
    // This is not the recommended way, as the page might miss information, but
    // there are cases where we still want to show the page to the user.
    this.snackBarRef.dismiss();
  }

  copyError() {
    this.clipboard.copy(this.error);
    this.copied = true;
  }
}
