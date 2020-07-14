import {NgModule} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {ClientAddLabelDialog} from './client_add_label_dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {FormsModule} from '@angular/forms';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
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
