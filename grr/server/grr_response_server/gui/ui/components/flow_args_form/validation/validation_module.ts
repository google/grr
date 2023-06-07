import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';

import {LiteralPathGlobExpressionWarning} from './literal_path_glob_expression_warning';

@NgModule({
  imports: [
    CommonModule,
    MatLegacyFormFieldModule,
  ],
  declarations: [
    LiteralPathGlobExpressionWarning,
  ],
  exports: [
    LiteralPathGlobExpressionWarning,
  ]
})
export class ValidationModule {
}
