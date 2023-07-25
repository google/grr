import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ByteComponentsModule} from '../../../../components/form/byte_input/module';
import {DurationComponentsModule} from '../../../../components/form/duration_input/module';
import {RolloutFormModule} from '../../../../components/hunt/rollout_form/module';

import {ParamsForm} from './params_form';


@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // clang-format off
    // keep-sorted start block=yes
    ByteComponentsModule,
    CommonModule,
    DurationComponentsModule,
    FormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RolloutFormModule,
    // keep-sorted end
    // clang-format on
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
