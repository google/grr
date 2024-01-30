import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatSnackBarModule} from '@angular/material/snack-bar';

import {SnackBarErrorHandler} from './error_handler';
import {ErrorSnackBar, WINDOW} from './error_snackbar';

@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ClipboardModule,
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
    // keep-sorted end
  ],
  declarations: [ErrorSnackBar],
  providers: [
    {provide: WINDOW, useFactory: () => window},
    {provide: SnackBarErrorHandler},
  ],
  exports: [ErrorSnackBar],
})
export class ErrorSnackBarModule {}
