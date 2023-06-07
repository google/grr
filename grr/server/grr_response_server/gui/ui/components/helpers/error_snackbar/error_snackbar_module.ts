import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacySnackBarModule} from '@angular/material/legacy-snack-bar';

import {SnackBarErrorHandler} from './error_handler';
import {ErrorSnackBar, WINDOW} from './error_snackbar';

@NgModule({
  imports: [
    CommonModule,
    ClipboardModule,
    MatIconModule,
    MatLegacyButtonModule,
    MatLegacySnackBarModule,
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
