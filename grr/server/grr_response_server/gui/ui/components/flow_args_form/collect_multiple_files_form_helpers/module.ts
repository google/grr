import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';
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
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    BrowserAnimationsModule,
    ByteComponentsModule,
    CommonModule,
    DateTimeInputModule,
    FormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    RouterModule,
    // keep-sorted end
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
export class HelpersModule {}
