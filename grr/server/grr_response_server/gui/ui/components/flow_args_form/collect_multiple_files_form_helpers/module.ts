import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyButtonModule} from '@angular/material/legacy-button';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacySelectModule} from '@angular/material/legacy-select';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ByteComponentsModule} from '../../../components/form/byte_input/module';
import {DateTimeInputModule} from '../../../components/form/date_time_input/module';

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
    ByteComponentsModule,
    // Angular Material modules.
    MatLegacyCardModule,
    MatLegacyButtonModule,
    MatLegacyFormFieldModule,
    MatLegacySelectModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyTooltipModule,
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
