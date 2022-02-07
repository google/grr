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

import {ParamsForm} from './params_form';


@NgModule({
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    ReactiveFormsModule,
    CommonModule,
    MatButtonToggleModule,
    FormsModule,
    ByteComponentsModule,
    DurationComponentsModule,
    MatTooltipModule,
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
