import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyProgressSpinnerModule} from '@angular/material/legacy-progress-spinner';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {FlowPickerModule} from '../../components/flow_picker/module';
import {SubmitOnMetaEnterModule} from '../form/submit_on_meta_enter/submit_on_meta_enter_module';

import {FlowForm} from './flow_form';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    CommonModule,
    FormsModule,
    OverlayModule,
    ReactiveFormsModule,
    RouterModule,

    MatLegacyButtonModule,
    MatLegacyCardModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyProgressSpinnerModule,
    MatLegacyTooltipModule,

    SubmitOnMetaEnterModule,
    FlowArgsFormModule,
    FlowPickerModule,
  ],
  declarations: [
    FlowForm,
  ],
  exports: [
    FlowForm,
  ],
})
export class FlowFormModule {
}
