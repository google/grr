import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';

import {ErrorSnackbar, WINDOW} from './error_snackbar';

@NgModule({
  imports: [CommonModule, ClipboardModule, MatIconModule, MatButtonModule],
  declarations: [ErrorSnackbar],
  providers: [{provide: WINDOW, useFactory: () => window}],
  exports: [ErrorSnackbar]
})
export class ErrorSnackbarModule {
}
