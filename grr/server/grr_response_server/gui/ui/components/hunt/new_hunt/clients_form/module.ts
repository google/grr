import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCheckboxModule} from '@angular/material/legacy-checkbox';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';
import {MatLegacySelectModule} from '@angular/material/legacy-select';

import {ClientsForm} from './clients_form';


@NgModule({
  imports: [
    MatLegacyAutocompleteModule,
    MatLegacyButtonModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyCheckboxModule,
    MatLegacyMenuModule,
    ReactiveFormsModule,
    CommonModule,
    MatLegacySelectModule,
    FormsModule,
  ],
  declarations: [
    ClientsForm,
  ],
  exports: [
    ClientsForm,
  ],
})
export class ClientsFormModule {
}
