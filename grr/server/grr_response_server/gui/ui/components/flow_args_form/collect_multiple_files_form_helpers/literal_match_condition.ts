import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup, Validators} from '@angular/forms';

import {FileFinderContentsLiteralMatchCondition, FileFinderContentsLiteralMatchConditionMode} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';

/** Form that configures a literal match condition. */
@Component({
  selector: 'literal-match-condition',
  templateUrl: './literal_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LiteralMatchCondition {
  readonly FileFinderContentsLiteralMatchConditionMode =
      FileFinderContentsLiteralMatchConditionMode;

  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup() {
    return this.controlContainer.control as
        ReturnType<typeof createLiteralMatchFormGroup>;
  }
}

/** Initializes a form group corresponding to the literal match condition. */
export function createLiteralMatchFormGroup() {
  return new FormGroup({
    // TODO: Writing existing values does not work - they need to
    // be base64 decoded?
    literal: new FormControl(
        '', {nonNullable: true, validators: Validators.required}),
    mode: new FormControl(
        FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
        {nonNullable: true}),
  });
}

/**
 * Converts raw form values to FileFinderContentsLiteralMatchCondition.
 */
export function formValuesToFileFinderContentsLiteralMatchCondition(
    rawFormValues: ReturnType<typeof createLiteralMatchFormGroup>['value']):
    FileFinderContentsLiteralMatchCondition {
  return {
    ...rawFormValues,
    literal: encodeStringToBase64(rawFormValues.literal ?? ''),
  };
}
