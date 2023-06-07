import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyDialogModule} from '@angular/material/legacy-dialog';
import {MatLegacyInputModule} from '@angular/material/legacy-input';

import {FlowArgsFormModule} from '../flow_args_form/module';

import {FlowArgsView} from './flow_args_view';

/** Angular Module. */
@NgModule({
  imports: [
    CommonModule,
    MatLegacyButtonModule,
    MatLegacyDialogModule,
    MatLegacyInputModule,
    MatLegacyAutocompleteModule,
    ReactiveFormsModule,
    FlowArgsFormModule,
    FormsModule,
  ],
  declarations: [
    FlowArgsView,
  ],
  exports: [
    FlowArgsView,
  ]
})
export class FlowArgsViewModule {
}
