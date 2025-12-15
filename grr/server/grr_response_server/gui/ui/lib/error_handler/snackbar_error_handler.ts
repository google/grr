import {ErrorHandler, inject, Injectable} from '@angular/core';
import {MatSnackBar} from '@angular/material/snack-bar';

import {ErrorSnackBar} from './error_snackbar/error_snackbar';

/** Error handler that shows the error message in a SnackBar. */
@Injectable({providedIn: 'root'})
export class SnackBarErrorHandler extends ErrorHandler {
  readonly snackBar = inject(MatSnackBar);

  override handleError(error: unknown) {
    console.error(error);

    if (error instanceof Error) {
      error = error.message;
    }
    this.snackBar.openFromComponent(ErrorSnackBar, {data: String(error)});
  }
}
