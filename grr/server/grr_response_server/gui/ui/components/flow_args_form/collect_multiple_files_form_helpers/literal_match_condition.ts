import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup, Validators} from '@angular/forms';

import {FileFinderContentsLiteralMatchCondition, FileFinderContentsMatchConditionMode} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';

declare interface LiteralMatchRawFormValues {
  readonly literal: string;
  readonly mode: FileFinderContentsMatchConditionMode;
  readonly length: number;
}

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

/**
 * Converts raw form values to FileFinderContentsLiteralMatchCondition.
 */
export function formValuesToFileFinderContentsLiteralMatchCondition(
    rawFormValues: LiteralMatchRawFormValues):
    FileFinderContentsLiteralMatchCondition {
  return {
    ...rawFormValues,
    literal: encodeStringToBase64(rawFormValues.literal),
  };
}
