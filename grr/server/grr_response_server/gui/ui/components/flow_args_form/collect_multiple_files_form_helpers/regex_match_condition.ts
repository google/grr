import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup, Validators} from '@angular/forms';

import {FileFinderContentsRegexMatchCondition, FileFinderContentsRegexMatchConditionMode} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';

/** Form that configures a regex match condition. */
@Component({
  selector: 'regex-match-condition',
  templateUrl: './regex_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegexMatchCondition {
  readonly FileFinderContentsRegexMatchConditionMode =
      FileFinderContentsRegexMatchConditionMode;

  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup() {
    return this.controlContainer.control as
        ReturnType<typeof createRegexMatchFormGroup>;
  }
}

/** Initializes a form group corresponding to the regex match condition. */
export function createRegexMatchFormGroup() {
  return new FormGroup({
    // TODO: Writing existing values does not work - they need to
    // be base64 decoded?
    regex: new FormControl(
        '', {nonNullable: true, validators: [Validators.required]}),
    mode: new FormControl(
        FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
        {nonNullable: true}),
    length: new FormControl(20_000_000, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(0)]
    }),
  });
}

/**
 * Converts raw form values to FileFinderContentsRegexMatchCondition; coerces
 * length to an integer.
 */
export function formValuesToFileFinderContentsRegexMatchCondition(
    rawFormValues: ReturnType<typeof createRegexMatchFormGroup>['value']):
    FileFinderContentsRegexMatchCondition {
  return {
    ...rawFormValues,
    regex: encodeStringToBase64(rawFormValues.regex ?? ''),
    length: Math.floor(rawFormValues.length ?? 0).toString(),
  };
}
