import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures a regex match condition. */
@Component({
  selector: 'regex-match-condition',
  templateUrl: './regex_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegexMatchCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
