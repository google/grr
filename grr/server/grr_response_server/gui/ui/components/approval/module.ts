import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../client/approval_chip/approval_chip_module';
import {UserImageModule} from '../user_image/module';

import {Approval} from './approval';

/**
 * Module for the approval details component.
 */
@NgModule({
  imports: [
    BrowserAnimationsModule,
    ClipboardModule,
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,

    MatAutocompleteModule,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,

    ApprovalChipModule,
    UserImageModule,
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
