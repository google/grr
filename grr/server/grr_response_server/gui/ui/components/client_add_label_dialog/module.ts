import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatInputModule} from '@angular/material/input';

import {ClientAddLabelDialog} from './client_add_label_dialog';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatInputModule,
    MatAutocompleteModule,
    ReactiveFormsModule,
  ],
  declarations: [
    ClientAddLabelDialog,
  ],
  entryComponents: [
    ClientAddLabelDialog,
  ],
  exports: [
    ClientAddLabelDialog,
  ],
})
export class ClientAddLabelDialogModule {
}
