import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {
  ControlContainer,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';

import {FileFinderContentsLiteralMatchConditionMode} from '../../../../lib/api/api_interfaces';
import {FormErrors, requiredInput} from '../../form/form_validation';

/** Form that configures a literal match condition. */
@Component({
  selector: 'literal-match-subform',
  templateUrl: './literal_match_subform.ng.html',
  styleUrls: ['subform_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LiteralMatchSubform {
  protected readonly controlContainer = inject(ControlContainer);

  readonly FileFinderContentsLiteralMatchConditionMode =
    FileFinderContentsLiteralMatchConditionMode;

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createLiteralMatchFormGroup
    >;
  }
}

/** Initializes a form group corresponding to the literal match condition. */
export function createLiteralMatchFormGroup() {
  return new FormGroup({
    // TODO: Writing existing values does not work - they need to
    // be base64 decoded?
    literal: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    mode: new FormControl(
      FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
      {nonNullable: true},
    ),
  });
}
