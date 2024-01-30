import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatNativeDateModule} from '@angular/material/core';
import {MatDatepickerModule} from '@angular/material/datepicker';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatMenuModule} from '@angular/material/menu';

import {DateTimeInput} from './date_time_input';
import {DateTimeInputToggle} from './date_time_input_toggle';

/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatChipsModule,
    MatDatepickerModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatNativeDateModule,
    // keep-sorted end
  ],
  declarations: [DateTimeInput, DateTimeInputToggle],
  exports: [DateTimeInput, DateTimeInputToggle],
})
export class DateTimeInputModule {}
