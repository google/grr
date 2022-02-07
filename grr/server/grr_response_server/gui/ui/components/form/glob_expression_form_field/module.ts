import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {GlobExpressionExplanation} from './glob_expression_explanation';
import {GlobExpressionInput} from './glob_expression_input';

/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
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
