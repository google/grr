import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {GlobExpressionExplanation} from './glob_expression_explanation';
import {GlobExpressionInput} from './glob_expression_input';

/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    // TODO: re-enable clang format when solved.
    // prettier-ignore
    // keep-sorted start block=yes
    CommonModule,
    FormsModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
    // keep-sorted end
  ],
  declarations: [GlobExpressionExplanation, GlobExpressionInput],
  exports: [GlobExpressionExplanation, GlobExpressionInput],
})
export class GlobExpressionExplanationModule {}
