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
import {RouterModule} from '@angular/router';

import {DurationComponentsModule} from '../../components/form/duration_input/module';
import {ApprovalChipModule} from '../approval_chip/approval_chip_module';
import {SubmitOnMetaEnterModule} from '../form/submit_on_meta_enter/submit_on_meta_enter_module';
import {TextWithLinksModule} from '../helpers/text_with_links/text_with_links_module';
import {UserImageModule} from '../user_image/module';

import {ApprovalCard} from './approval_card';

/**
 * Module for the approval details component.
 */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    ApprovalChipModule,
    ClipboardModule,
    CommonModule,
    DurationComponentsModule,
    FormsModule,
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
    ReactiveFormsModule,
    RouterModule,
    SubmitOnMetaEnterModule,
    TextWithLinksModule,
    UserImageModule,
    // keep-sorted end
  ],
  declarations: [ApprovalCard],
  exports: [ApprovalCard],
})
export class ApprovalCardModule {}
