import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';

import {GlobExpressionExplanation} from './glob_expression_explanation';

/** Module for GlobExpressionExplanation and related code. */
@NgModule({
  imports: [
    CommonModule,
  ],
  declarations: [
    GlobExpressionExplanation,
  ],
  exports: [
    GlobExpressionExplanation,
  ],
})
export class GlobExpressionExplanationModule {
}
