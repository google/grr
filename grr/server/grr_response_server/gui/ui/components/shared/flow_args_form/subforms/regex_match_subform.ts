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

import {FileFinderContentsRegexMatchConditionMode} from '../../../../lib/api/api_interfaces';
import {FormErrors, minValue, requiredInput} from '../../form/form_validation';

/** Form that configures a regex match condition. */
@Component({
  selector: 'regex-match-subform',
  templateUrl: './regex_match_subform.ng.html',
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
export class RegexMatchSubform {
  protected readonly controlContainer = inject(ControlContainer);

  readonly FileFinderContentsRegexMatchConditionMode =
    FileFinderContentsRegexMatchConditionMode;

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createRegexMatchFormGroup
    >;
  }
}

/** Initializes a form group corresponding to the regex match condition. */
export function createRegexMatchFormGroup() {
  return new FormGroup({
    // TODO: Writing existing values does not work - they need to
    // be base64 decoded?
    regex: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    mode: new FormControl(FileFinderContentsRegexMatchConditionMode.FIRST_HIT, {
      nonNullable: true,
    }),
    length: new FormControl(20_000_000, {
      nonNullable: true,
      validators: [requiredInput(), minValue(0)],
    }),
  });
}
