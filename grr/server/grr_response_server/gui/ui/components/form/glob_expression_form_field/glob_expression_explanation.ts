import {ChangeDetectionStrategy, Component, Input, OnChanges, SimpleChanges} from '@angular/core';
import {ExplainGlobExpressionService} from '@app/lib/service/explain_glob_expression_service/explain_glob_expression_service';


/** mat-form-field for GlobExpression inputs. */
@Component({
  selector: 'glob-expression-explanation',
  templateUrl: './glob_expression_explanation.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ExplainGlobExpressionService],
})
export class GlobExpressionExplanation implements OnChanges {
  @Input() globExpression?: string;

  @Input() clientId?: string;

  readonly explanation$ = this.globExpressionService.explanation$;

  constructor(
      private readonly globExpressionService: ExplainGlobExpressionService,
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (this.clientId !== undefined && this.globExpression !== undefined) {
      this.globExpressionService.explain(this.clientId, this.globExpression);
    }
  }
}
