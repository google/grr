import {Component, HostBinding, Input} from '@angular/core';

/** Shows a warning if the input path contains %%. */
@Component({
  standalone: false,
  selector: 'app-literal-glob-expression-warning',
  templateUrl: './literal_glob_expression_warning.ng.html',
  styleUrls: ['./literal_glob_expression_warning.scss'],
})
export class LiteralGlobExpressionWarning {
  @Input() path: string | undefined | null;

  @HostBinding('hidden')
  get hideWarning() {
    const includesTrigger = this.path?.includes('*') ?? false;
    return !includesTrigger;
  }
}
