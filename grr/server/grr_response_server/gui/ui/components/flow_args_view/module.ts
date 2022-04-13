import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatInputModule} from '@angular/material/input';

import {FlowArgsFormModule} from '../flow_args_form/module';

import {FlowArgsView} from './flow_args_view';

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
    FlowArgsView,
  ],
  entryComponents: [
    FlowArgsView,
  ],
  exports: [
    FlowArgsView,
  ],
})
export class FlowArgsViewModule {
}
