import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures a literal match condition. */
@Component({
  selector: 'literal-match-condition',
  templateUrl: './literal_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LiteralMatchCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
