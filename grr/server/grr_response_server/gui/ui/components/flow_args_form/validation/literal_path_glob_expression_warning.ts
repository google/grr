import {Component, HostBinding, Input} from '@angular/core';

/** Shows a warning if the input path contains %%. */
@Component({
  selector: 'app-literal-path-glob-expression-warning',
  templateUrl: './literal_path_glob_expression_warning.ng.html',
  styleUrls: ['./literal_path_glob_expression_warning.scss']
})
export class LiteralPathGlobExpressionWarning {
  @Input() path: string|undefined|null;

  @HostBinding('hidden')
  get hideWarning() {
    const includesTrigger = this.path?.includes('%%') ?? false;
    return !includesTrigger;
  }
}
