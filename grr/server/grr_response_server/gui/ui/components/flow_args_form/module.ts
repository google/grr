import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {BrowserHistoryFlowForm} from '@app/components/flow_args_form/browser_history_flow_form';

import {FallbackFlowArgsForm} from './fallback_flow_args_form';
import {FlowArgsForm} from './flow_args_form';

/** Module for the FlowArgsForm component. */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatCheckboxModule,
    ReactiveFormsModule,
  ],
  declarations: [
    FlowArgsForm,
    BrowserHistoryFlowForm,
    FallbackFlowArgsForm,
  ],
  entryComponents: [
    BrowserHistoryFlowForm,
    FallbackFlowArgsForm,
  ],
  exports: [
    FlowArgsForm,
  ],
})
export class FlowArgsFormModule {
}