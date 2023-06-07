import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {RolloutForm} from './rollout_form';

@NgModule({
  imports: [
    CommonModule,
    MatButtonToggleModule,
    ReactiveFormsModule,
    FormsModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyTooltipModule,
  ],
  declarations: [
    RolloutForm,
  ],
  exports: [
    RolloutForm,
  ]
})
export class RolloutFormModule {
}
