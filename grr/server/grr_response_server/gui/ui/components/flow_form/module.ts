import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {FlowArgsFormModule} from '@app/components/flow_args_form/module';
import {FlowPickerModule} from '@app/components/flow_picker/module';

import {FlowForm} from './flow_form';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    CommonModule,
    MatInputModule,
    FlowPickerModule,
    FlowArgsFormModule,
    ReactiveFormsModule,
    FormsModule,
    MatButtonModule,
    OverlayModule,
    MatCardModule,
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
