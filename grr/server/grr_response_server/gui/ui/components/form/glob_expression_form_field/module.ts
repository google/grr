import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatLegacyAutocompleteModule} from '@angular/material/legacy-autocomplete';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';

import {GlobExpressionExplanation} from './glob_expression_explanation';
import {GlobExpressionInput} from './glob_expression_input';

/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatLegacyAutocompleteModule,
    MatLegacyFormFieldModule,
    MatLegacyInputModule,
    MatLegacyTooltipModule,
  ],
  declarations: [
    GlobExpressionExplanation,
    GlobExpressionInput,
  ],
  exports: [
    GlobExpressionExplanation,
    GlobExpressionInput,
  ],
})
export class GlobExpressionExplanationModule {
}
