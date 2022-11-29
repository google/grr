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
    CommonModule,
    ClipboardModule,
    MatIconModule,
    MatButtonModule,
    MatSnackBarModule,
  ],
  declarations: [ErrorSnackBar],
  providers: [
    {provide: WINDOW, useFactory: () => window},
    {provide: SnackBarErrorHandler},
  ],
  exports: [ErrorSnackBar]
})
export class ErrorSnackBarModule {
}
