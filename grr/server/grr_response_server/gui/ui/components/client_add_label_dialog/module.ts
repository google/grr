import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {SubmitOnMetaEnterModule} from '../form/submit_on_meta_enter/submit_on_meta_enter_module';

import {ClientAddLabelDialog} from './client_add_label_dialog';

/**
 * Module for the client details component.
 */
@NgModule({
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatLegacyAutocompleteModule,
    MatLegacyButtonModule,
    MatLegacyDialogModule,
    MatLegacyInputModule,
    MatLegacyTooltipModule,
    SubmitOnMetaEnterModule,
  ],
  declarations: [
    ClientAddLabelDialog,
  ],
  exports: [
    ClientAddLabelDialog,
  ]
})
export class ClientAddLabelDialogModule {
}
