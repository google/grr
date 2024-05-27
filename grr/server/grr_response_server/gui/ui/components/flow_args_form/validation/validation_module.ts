import {CommonModule} from '@angular/common';
import {NgModule} from '@angular/core';
import {MatFormFieldModule} from '@angular/material/form-field';

import {LiteralGlobExpressionWarning} from './literal_glob_expression_warning';
import {LiteralKnowledgebaseExpressionWarning} from './literal_knowledgebase_expression_warning';

@NgModule({
  imports: [CommonModule, MatFormFieldModule],
  declarations: [
    LiteralKnowledgebaseExpressionWarning,
    LiteralGlobExpressionWarning,
  ],
  exports: [
    LiteralKnowledgebaseExpressionWarning,
    LiteralGlobExpressionWarning,
  ],
})
export class ValidationModule {}
