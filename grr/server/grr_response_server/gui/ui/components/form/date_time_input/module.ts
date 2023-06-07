import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyChipsModule} from '@angular/material/legacy-chips';
import {MatLegacyNativeDateModule} from '@angular/material/legacy-core';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyMenuModule} from '@angular/material/legacy-menu';

import {DateTimeInput} from './date_time_input';
import {DateTimeInputToggle} from './date_time_input_toggle';



/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    MatLegacyChipsModule,
    MatIconModule,
    MatLegacyInputModule,
    MatDatepickerModule,
    MatLegacyNativeDateModule,
    MatLegacyMenuModule,
  ],
  declarations: [
    DateTimeInput,
    DateTimeInputToggle,
  ],
  exports: [
    DateTimeInput,
    DateTimeInputToggle,
  ],
})
export class DateTimeInputModule {
}
