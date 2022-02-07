import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {FlowPickerModule} from '../../components/flow_picker/module';

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

    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,

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
