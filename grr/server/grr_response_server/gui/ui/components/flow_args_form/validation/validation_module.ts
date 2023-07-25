import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';

import {LiteralPathGlobExpressionWarning} from './literal_path_glob_expression_warning';

@NgModule({
  imports: [
    CommonModule,
    MatFormFieldModule,
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
