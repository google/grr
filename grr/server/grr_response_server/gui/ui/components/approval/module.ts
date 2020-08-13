import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ScheduledFlowListModule} from '../scheduled_flow_list/module';

import {Approval} from './approval';

/**
 * Module for the approval details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    RouterModule,
    MatChipsModule,
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatIconModule,
    MatButtonModule,
    FormsModule,
    ReactiveFormsModule,
    ScheduledFlowListModule,
    ClipboardModule,
  ],
  declarations: [
    Approval,
  ],
  exports: [
    Approval,
  ],
})
export class ApprovalModule {
}
