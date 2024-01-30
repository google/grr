import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';

import {isNonNull} from '../../../lib/preconditions';
import {ExplainGlobExpressionService} from '../../../lib/service/explain_glob_expression_service/explain_glob_expression_service';

/** GlobExplanationMode controls how the explained glob is displayed. */
export enum GlobExplanationMode {
  // Substitutes globs by an explained example if available.
  ONE_EXAMPLE_VISIBLE,

  // Display the glob (highlighted), and shows examples on demmand (toooltip).
  ONLY_GLOB_VISIBLE,
}

/** mat-form-field for GlobExpression inputs. */
@Component({
  selector: 'glob-expression-explanation',
  templateUrl: './glob_expression_explanation.ng.html',
  styleUrls: ['./glob_expression_explanation.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ExplainGlobExpressionService],
})
export class GlobExpressionExplanation implements OnChanges {
  protected readonly GlobExplanationMode = GlobExplanationMode;

  @Input() globExpression?: string;

  @Input() clientId?: string | null;

  @Input()
  explanationMode?: GlobExplanationMode =
    GlobExplanationMode.ONE_EXAMPLE_VISIBLE;

  readonly explanation$ = this.globExpressionService.explanation$;

  constructor(
    private readonly globExpressionService: ExplainGlobExpressionService,
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (isNonNull(this.clientId) && isNonNull(this.globExpression)) {
      this.globExpressionService.explain(this.clientId, this.globExpression);
    }
  }
}
