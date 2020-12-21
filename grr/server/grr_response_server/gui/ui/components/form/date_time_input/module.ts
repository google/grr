import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule} from '@angular/forms';
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
    CommonModule,
    FormsModule,
    MatChipsModule,
    MatIconModule,
    MatInputModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatMenuModule,
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
