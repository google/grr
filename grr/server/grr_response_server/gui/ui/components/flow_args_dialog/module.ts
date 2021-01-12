import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatInputModule} from '@angular/material/input';

import {FlowArgsFormModule} from '../flow_args_form/module';

import {FlowArgsDialog} from './flow_args_dialog';

/** Angular Module. */
@NgModule({
  imports: [
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatInputModule,
    MatAutocompleteModule,
    ReactiveFormsModule,
    FlowArgsFormModule,
    FormsModule,
  ],
  declarations: [
    FlowArgsDialog,
  ],
  entryComponents: [
    FlowArgsDialog,
  ],
  exports: [
    FlowArgsDialog,
  ],
})
export class FlowArgsDialogModule {
}
