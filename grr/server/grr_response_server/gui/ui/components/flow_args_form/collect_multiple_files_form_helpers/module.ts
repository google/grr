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

import {AccessTimeCondition} from './access_time_condition';
import {ConditionPanel} from './condition_panel';
import {ExtFlagsCondition} from './ext_flags_condition';
import {InodeChangeTimeCondition} from './inode_change_time_condition';
import {LiteralMatchCondition} from './literal_match_condition';
import {ModificationTimeCondition} from './modification_time_condition';
import {RegexMatchCondition} from './regex_match_condition';
import {SizeCondition} from './size_condition';

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
    // Angular Material modules.
    MatCardModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
  ],
  declarations: [
    ConditionPanel,
    AccessTimeCondition,
    ExtFlagsCondition,
    InodeChangeTimeCondition,
    LiteralMatchCondition,
    ModificationTimeCondition,
    RegexMatchCondition,
    SizeCondition,
  ],
  exports: [
    ConditionPanel,
    AccessTimeCondition,
    ExtFlagsCondition,
    InodeChangeTimeCondition,
    LiteralMatchCondition,
    ModificationTimeCondition,
    RegexMatchCondition,
    SizeCondition,
  ],
})
export class HelpersModule {
}
