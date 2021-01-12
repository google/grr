import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowArgsDialogModule} from '../flow_args_dialog/module';
import {FlowDetailsModule} from '../flow_details/module';

import {FlowList} from './flow_list';


/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    // Angular builtin modules.
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    ReactiveFormsModule,
    FormsModule,

    // Angular material modules.
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,

    // GRR modules.
    FlowArgsDialogModule,
    FlowDetailsModule,
  ],
  declarations: [
    FlowList,
  ],
  exports: [
    FlowList,
  ],
})
export class FlowListModule {
}
