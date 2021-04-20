import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup, Validators} from '@angular/forms';
import {FileFinderContentsMatchConditionMode, FileFinderContentsRegexMatchCondition} from '@app/lib/api/api_interfaces';

/** Represents raw values produced by the time range form. */
export interface RegexMatchRawFormValues {
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

  get formGroup(): FormGroup {
    return this.controlContainer.control as FormGroup;
  }
}

/** Initializes a form group corresponding to the regex match condition. */
export function createRegexMatchFormGroup(): FormGroup {
  // Default length (for how far into the file to search) is 20 MB.
  const DEFAULT_LENGTH = 20_000_000;

  return new FormGroup({
    regex: new FormControl(null, Validators.required),
    mode: new FormControl(FileFinderContentsMatchConditionMode.FIRST_HIT),
    length: new FormControl(
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
    length: Math.floor(rawFormValues.length),
  };
}
