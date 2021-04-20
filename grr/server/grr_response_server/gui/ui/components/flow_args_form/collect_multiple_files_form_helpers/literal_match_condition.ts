import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup, Validators} from '@angular/forms';
import {FileFinderContentsMatchConditionMode} from '@app/lib/api/api_interfaces';

/** Form that configures a literal match condition. */
@Component({
  selector: 'literal-match-condition',
  templateUrl: './literal_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LiteralMatchCondition {
  readonly FileFinderContentsMatchConditionMode =
      FileFinderContentsMatchConditionMode;

  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup(): FormGroup {
    return this.controlContainer.control as FormGroup;
  }
}

/** Initializes a form group corresponding to the literal match condition. */
export function createLiteralMatchFormGroup(): FormGroup {
  return new FormGroup({
    literal: new FormControl(null, Validators.required),
    mode: new FormControl(FileFinderContentsMatchConditionMode.FIRST_HIT),
  });
}
