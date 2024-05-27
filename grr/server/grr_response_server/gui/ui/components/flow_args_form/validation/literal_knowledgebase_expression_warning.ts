import {Component, HostBinding, Input} from '@angular/core';

/** Shows a warning if the input path contains %%. */
@Component({
  selector: 'app-literal-knowledgebase-expression-warning',
  templateUrl: './literal_knowledgebase_expression_warning.ng.html',
  styleUrls: ['./literal_knowledgebase_expression_warning.scss'],
})
export class LiteralKnowledgebaseExpressionWarning {
  @Input() path: string | undefined | null;

  @HostBinding('hidden')
  get hideWarning() {
    const includesTrigger = this.path?.includes('%%') ?? false;
    return !includesTrigger;
  }
}
