import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {ByteComponentsModule} from '../../../../components/form/byte_input/module';
import {DurationComponentsModule} from '../../../../components/form/duration_input/module';
import {RolloutFormModule} from '../../../../components/hunt/rollout_form/module';

import {ParamsForm} from './params_form';


@NgModule({
  imports: [
    MatLegacyButtonModule,
    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    ReactiveFormsModule,
    CommonModule,
    MatButtonToggleModule,
    FormsModule,
    ByteComponentsModule,
    DurationComponentsModule,
    MatLegacyTooltipModule,
    RolloutFormModule,
  ],
  declarations: [
    ParamsForm,
  ],
  exports: [
    ParamsForm,
  ],
})
export class ParamsFormModule {
}
