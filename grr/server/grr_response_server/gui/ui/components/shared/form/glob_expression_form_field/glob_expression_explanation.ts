import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  Input,
  OnChanges,
  SimpleChanges,
} from '@angular/core';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ExplainGlobExpressionService} from '../../../../lib/service/explain_glob_expression_service/explain_glob_expression_service';

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
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatTooltipModule,
    MatAutocompleteModule,
  ],
  providers: [ExplainGlobExpressionService],
})
export class GlobExpressionExplanation implements OnChanges {
  protected readonly GlobExplanationMode = GlobExplanationMode;

  @Input() globExpression?: string;

  @Input() clientId?: string | null;

  @Input()
  explanationMode?: GlobExplanationMode =
    GlobExplanationMode.ONE_EXAMPLE_VISIBLE;

  readonly explanation$;

  constructor(
    private readonly globExpressionService: ExplainGlobExpressionService,
  ) {
    this.explanation$ = this.globExpressionService.explanation$;
  }

  ngOnChanges(changes: SimpleChanges) {
    if (this.clientId != null && this.globExpression != null) {
      this.globExpressionService.explain(this.clientId, this.globExpression);
    }
  }
}
