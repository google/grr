import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacySelectModule} from '@angular/material/legacy-select';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowDetailsModule} from '../flow_details/module';
import {InfiniteListModule} from '../helpers/infinite_list/infinite_list_module';
import {TimestampModule} from '../timestamp/module';

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
    MatLegacyButtonModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyCardModule,
    MatLegacyProgressSpinnerModule,
    MatLegacySelectModule,

    // GRR modules.
    FlowDetailsModule,
    InfiniteListModule,
    TimestampModule,
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
