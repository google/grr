import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, UntypedFormControl, UntypedFormGroup, Validators} from '@angular/forms';

import {FileFinderContentsMatchConditionMode, FileFinderContentsRegexMatchCondition} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';

/** Represents raw values produced by the time range form. */
export declare interface RegexMatchRawFormValues {
  readonly regex: string;
  readonly mode: FileFinderContentsMatchConditionMode;
  readonly length: number;
}

/** Form that configures a regex match condition. */
@Component({
  selector: 'regex-match-condition',
  templateUrl: './regex_match_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegexMatchCondition {
  readonly FileFinderContentsMatchConditionMode =
      FileFinderContentsMatchConditionMode;

  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup(): UntypedFormGroup {
    return this.controlContainer.control as UntypedFormGroup;
  }
}

/** Initializes a form group corresponding to the regex match condition. */
export function createRegexMatchFormGroup(): UntypedFormGroup {
  // Default length (for how far into the file to search) is 20 MB.
  const DEFAULT_LENGTH = 20_000_000;

  return new UntypedFormGroup({
    regex: new UntypedFormControl(null, Validators.required),
    mode:
        new UntypedFormControl(FileFinderContentsMatchConditionMode.FIRST_HIT),
    length: new UntypedFormControl(
        DEFAULT_LENGTH, [Validators.required, Validators.min(0)]),
  });
}

/**
 * Converts raw form values to FileFinderContentsRegexMatchCondition; coerces
 * length to an integer.
 */
export function formValuesToFileFinderContentsRegexMatchCondition(
    rawFormValues: RegexMatchRawFormValues):
    FileFinderContentsRegexMatchCondition {
  return {
    ...rawFormValues,
    regex: encodeStringToBase64(rawFormValues.regex),
    length: Math.floor(rawFormValues.length),
  };
}
