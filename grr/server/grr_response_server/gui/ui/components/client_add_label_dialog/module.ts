import {NgModule} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {ClientAddLabelDialog} from './client_add_label_dialog';
import {MatInputModule} from '@angular/material/input';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {CommonModule} from '@angular/common';

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
  exports: [
    ClientAddLabelDialog,
  ],
})
export class ClientAddLabelDialogModule {
}
