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

import {ByteValueAccessor} from '../../form/byte_input/byte_value_accessor';
import {
  FormErrors,
  atLeastOneMustBeSet,
  minValue,
} from '../../form/form_validation';

const DEFAULT_MAX_FILE_SIZE = 20_000_000; // 20 MB

/** Form that configures a size condition. */
@Component({
  selector: 'file-size-range-subform',
  templateUrl: './file_size_range_subform.ng.html',
  styleUrls: ['subform_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    ByteValueAccessor,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileSizeRangeSubform {
  protected readonly controlContainer = inject(ControlContainer);

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createFileSizeRangeFormGroup
    >;
  }
}

/** Initializes a form group corresponding to the size condition. */
export function createFileSizeRangeFormGroup() {
  const minFileSize = new FormControl<number | null>(null, [minValue(1)]);
  const maxFileSize = new FormControl<number | null>(DEFAULT_MAX_FILE_SIZE, [
    minValue(1),
  ]);

  return new FormGroup(
    {minFileSize, maxFileSize},
    // TODO: Add check if values are in order.
    {validators: [atLeastOneMustBeSet([minFileSize, maxFileSize])]},
  );
}
