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
import {MatTooltipModule} from '@angular/material/tooltip';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ApprovalChipModule} from '../client/approval_chip/approval_chip_module';
import {SubmitOnMetaEnterModule} from '../form/submit_on_meta_enter/submit_on_meta_enter_module';
import {TextWithLinksModule} from '../helpers/text_with_links/text_with_links_module';
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
    MatTooltipModule,

    ApprovalChipModule,
    UserImageModule,
    SubmitOnMetaEnterModule,
    TextWithLinksModule,
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
