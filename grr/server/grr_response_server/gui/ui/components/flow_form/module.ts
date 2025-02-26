import {OverlayModule} from '@angular/cdk/overlay';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTooltipModule} from '@angular/material/tooltip';
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
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    FlowArgsFormModule,
    FlowPickerModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    OverlayModule,
    ReactiveFormsModule,
    RouterModule,
    SubmitOnMetaEnterModule,
    // keep-sorted end
  ],
  declarations: [FlowForm],
  exports: [FlowForm],
})
export class FlowFormModule {}
