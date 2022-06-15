import {ChangeDetectionStrategy, Component, EventEmitter, OnInit, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup} from '@angular/forms';
import {combineLatest, Observable, zip} from 'rxjs';
import {map, shareReplay} from 'rxjs/operators';

import {atLeastOneMustBeSet} from '../../../components/form/validators';
import {toByteUnit} from '../../form/byte_input/byte_conversion';

// Default max file size is 20 MB.
const DEFAULT_MAX_FILE_SIZE = 20_000_000;

declare interface FormattedFormValues {
  readonly min?: string;
  readonly max?: string;
}

declare interface HintFormattingData {
  readonly formattedBytesAtUnit: FormattedFormValues;
  readonly units: FormattedFormValues;
  readonly formattedRawBytes: FormattedFormValues;
}

/** Form that configures a size condition. */
@Component({
  selector: 'size-condition',
  templateUrl: './size_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SizeCondition implements OnInit {
  hintFormatting$?: Observable<HintFormattingData>;

  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup() {
    return this.controlContainer.control as
        ReturnType<typeof createSizeFormGroup>;
  }

  ngOnInit() {
    const formValues$ = this.formGroup.valueChanges.pipe(
        shareReplay({bufferSize: 1, refCount: true}));

    const bytesAndUnit$ = formValues$.pipe(map(values => {
      return {
        min: getByteUnit(values.minFileSize ?? undefined),
        max: getByteUnit(values.maxFileSize ?? undefined),
      };
    }));

    const formattedBytesAtUnit$ = bytesAndUnit$.pipe(map(bytesValues => {
      return {
        min: getFormattedBytes(bytesValues.min),
        max: getFormattedBytes(bytesValues.max),
      };
    }));

    const units$ = bytesAndUnit$.pipe(map(bytesValues => {
      return {
        min: getUnit(bytesValues.min),
        max: getUnit(bytesValues.max),
      };
    }));

    const formattedRawBytes$ = zip(formValues$, formattedBytesAtUnit$)
                                   .pipe(
                                       map(([values, formattedBytesAtUnit]) => {
                                         return {
                                           min: getFormattedRawBytes(
                                               formattedBytesAtUnit.min,
                                               values.minFileSize ?? undefined),
                                           max: getFormattedRawBytes(
                                               formattedBytesAtUnit.max,
                                               values.maxFileSize ?? undefined),
                                         };
                                       }),
                                   );

    this.hintFormatting$ =
        combineLatest([formattedBytesAtUnit$, units$, formattedRawBytes$])
            .pipe(
                map(([formattedBytesAtUnit, units, formattedRawBytes]) =>
                        ({formattedBytesAtUnit, units, formattedRawBytes})),
            );
  }
}

function getByteUnit(fileSize?: number): [number, string]|undefined {
  // Form value of 0 indicates that field is unset.
  if (!fileSize) return;
  return toByteUnit(fileSize, 'long');
}

function getFormattedBytes(bytesAndUnit?: [number, string]): string|undefined {
  if (bytesAndUnit == null) return;
  const [bytes] = bytesAndUnit;
  return bytes.toLocaleString();
}

function getUnit(bytesAndUnit?: [number, string]): string|undefined {
  if (bytesAndUnit == null) return;
  const [, unit] = bytesAndUnit;
  return unit;
}

/**
 * Returns raw bytes value or undefined, depending on whether user input matches
 * raw value (2mB vs 2000000).
 */
function getFormattedRawBytes(
    formattedBytesAtUnit?: string, fileSize?: number): string|undefined {
  if (formattedBytesAtUnit == null || fileSize == null) return;

  const formattedRawBytes = fileSize.toLocaleString();
  if (formattedBytesAtUnit === formattedRawBytes) return;

  return formattedRawBytes;
}

/** Initializes a form group corresponding to the size condition. */
export function createSizeFormGroup() {
  const minFileSize = new FormControl<number|null>(null);
  const maxFileSize = new FormControl<number|null>(DEFAULT_MAX_FILE_SIZE);

  return new FormGroup(
      {
        minFileSize,
        maxFileSize,
      },
      atLeastOneMustBeSet([minFileSize, maxFileSize]));
}
