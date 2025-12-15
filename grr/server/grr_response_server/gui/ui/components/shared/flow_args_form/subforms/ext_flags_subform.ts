import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  OnInit,
} from '@angular/core';
import {
  ControlContainer,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';
import {MatSelectModule} from '@angular/material/select';

import {safeTranslateOperatingSystem} from '../../../../lib/api/translation/flow';
import {OperatingSystem} from '../../../../lib/models/flow';
import {
  Flag,
  LINUX_FLAGS_ORDERED,
  OSX_FLAGS,
} from '../../../../lib/models/os_extended_flags';

interface ExtendedFlags extends Flag {
  selection: 'include' | 'exclude' | 'either';
}

/** Form that configures an ext flags condition. */
@Component({
  selector: 'ext-flags-subform',
  templateUrl: './ext_flags_subform.ng.html',
  styleUrls: ['./ext_flags_subform.scss', './subform_styles.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    MatSelectModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExtFlagsSubform implements OnInit {
  protected readonly controlContainer = inject(ControlContainer);

  readonly clientOs = input(null, {transform: safeTranslateOperatingSystem});

  readonly OperatingSystem = OperatingSystem;

  readonly extendedLinuxFlags: readonly ExtendedFlags[] =
    LINUX_FLAGS_ORDERED.map((flag) => ({...flag, selection: 'either'}));
  readonly extendedOsxFlags: readonly ExtendedFlags[] = OSX_FLAGS.map(
    (flag) => ({...flag, selection: 'either'}),
  );

  get formGroup() {
    return this.controlContainer.control as ReturnType<
      typeof createExtFlagsFormGroup
    >;
  }

  ngOnInit() {
    this.resetFormValues();
  }

  // Convert radio button selection to bit and update the form state.
  protected onExtFlagsChangeDarwin(): void {
    let includeBits = 0;
    let excludeBits = 0;
    for (const flag of this.extendedOsxFlags) {
      if (flag.selection === 'include') {
        includeBits |= flag.mask;
      }
      if (flag.selection === 'exclude') {
        excludeBits |= flag.mask;
      }
    }
    this.formGroup.controls.osxBitsSet.setValue(includeBits);
    this.formGroup.controls.osxBitsUnset.setValue(excludeBits);
  }

  // Convert radio button selection to bit and update the form state.
  protected onExtFlagsChangeLinux(): void {
    let includeBits = 0;
    let excludeBits = 0;
    for (const flag of this.extendedLinuxFlags) {
      if (flag.selection === 'include') {
        includeBits |= flag.mask;
      }
      if (flag.selection === 'exclude') {
        excludeBits |= flag.mask;
      }
    }
    this.formGroup.controls.linuxBitsSet.setValue(includeBits);
    this.formGroup.controls.linuxBitsUnset.setValue(excludeBits);
  }

  private resetFormValues(): void {
    this.resetDarwinForm(
      this.formGroup.controls.osxBitsSet.value,
      this.formGroup.controls.osxBitsUnset.value,
    );
    this.resetLinuxForm(
      this.formGroup.controls.linuxBitsSet.value,
      this.formGroup.controls.linuxBitsUnset.value,
    );
  }

  // Reset the radio buttons based on the given bit masks in the form state.
  private resetDarwinForm(includeBits: number, excludeBits: number): void {
    for (const flag of this.extendedOsxFlags) {
      if (flag.mask & includeBits) {
        flag.selection = 'include';
      } else if (flag.mask & excludeBits) {
        flag.selection = 'exclude';
      } else {
        flag.selection = 'either';
      }
    }
  }

  // Reset the radio buttons based on the given bit masks in the form state.
  private resetLinuxForm(includeBits: number, excludeBits: number): void {
    for (const flag of this.extendedLinuxFlags) {
      if (flag.mask & includeBits) {
        flag.selection = 'include';
      } else if (flag.mask & excludeBits) {
        flag.selection = 'exclude';
      } else {
        flag.selection = 'either';
      }
    }
  }
}

/** Initializes a form group corresponding to the ext flags condition. */
export function createExtFlagsFormGroup() {
  return new FormGroup({
    linuxBitsSet: new FormControl(0, {nonNullable: true}),
    linuxBitsUnset: new FormControl(0, {nonNullable: true}),
    osxBitsSet: new FormControl(0, {nonNullable: true}),
    osxBitsUnset: new FormControl(0, {nonNullable: true}),
  });
}
