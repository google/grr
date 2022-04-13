import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, UntypedFormControl, UntypedFormGroup, Validators} from '@angular/forms';

import {FileFinderContentsLiteralMatchCondition, FileFinderContentsMatchConditionMode} from '../../../lib/api/api_interfaces';
import {encodeStringToBase64} from '../../../lib/api_translation/primitive';

/** Form state of LiteralMatchCondition. */
export declare interface LiteralMatchRawFormValues {
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

  get formGroup(): UntypedFormGroup {
    return this.controlContainer.control as UntypedFormGroup;
  }
}

/** Initializes a form group corresponding to the literal match condition. */
export function createLiteralMatchFormGroup(): UntypedFormGroup {
  return new UntypedFormGroup({
    literal: new UntypedFormControl(null, Validators.required),
    mode:
        new UntypedFormControl(FileFinderContentsMatchConditionMode.FIRST_HIT),
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
