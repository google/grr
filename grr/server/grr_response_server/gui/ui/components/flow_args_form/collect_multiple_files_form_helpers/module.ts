import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {DateTimeInputModule} from '@app/components/form/date_time_input/module';

import {ConditionPanel} from './condition_panel';
import {ExtFlagsCondition} from './ext_flags_condition';
import {LiteralMatchCondition} from './literal_match_condition';
import {RegexMatchCondition} from './regex_match_condition';
import {SizeCondition} from './size_condition';
import {TimeRangeCondition} from './time_range_condition';

/**
 * Module for the flow_picker details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule,
    // Our custom modules.
    DateTimeInputModule,
    // Angular Material modules.
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  declarations: [
    ConditionPanel,
    ExtFlagsCondition,
    LiteralMatchCondition,
    TimeRangeCondition,
    RegexMatchCondition,
    SizeCondition,
  ],
  exports: [
    ConditionPanel,
    ExtFlagsCondition,
    LiteralMatchCondition,
    TimeRangeCondition,
    RegexMatchCondition,
    SizeCondition,
  ],
})
export class HelpersModule {
}
