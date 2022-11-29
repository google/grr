import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';
import {Observable} from 'rxjs';
import {filter, map, withLatestFrom} from 'rxjs/operators';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ReadLowLevelArgs} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {toByteUnit} from '../form/byte_input/byte_conversion';

function formatRawBytes(formattedBytesAtUnit: string, rawBytes: number) {
  const formattedRawBytes = rawBytes.toLocaleString();
  if (formattedBytesAtUnit === formattedRawBytes) {
    return undefined;
  } else {
    return formattedRawBytes;
  }
}

function makeControls() {
  return {
    path: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    // ByteValueAccessor inputs can be null when input is invalid.
    length: new FormControl<number|null>(null, {
      validators: [Validators.required, Validators.min(1)],
    }),
    offset: new FormControl<number|null>(null),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the read_low_level flow.
 */
@Component({
  selector: 'read_low_level-form',
  templateUrl: './read_low_level_form.ng.html',
  styleUrls: ['./read_low_level_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ReadLowLevelForm extends
    FlowArgumentForm<ReadLowLevelArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      length: formState.length?.toString(),
      offset: formState.offset?.toString(),
      path: formState.path?.trim(),
    };
  }

  private readonly lengthRawBytes$: Observable<number> = this.flowArgs$.pipe(
      // byteInput is guaranteed to return a number.
      // It uses `parseByteString` from ../form/byte_input/byte_conversion.
      map(values => Number(values.length)),
      filter(isNonNull),
  );
  private readonly offsetRawBytes$: Observable<number> = this.flowArgs$.pipe(
      // byteInput is guaranteed to return a number.
      // It uses `parseByteString` from ../form/byte_input/byte_conversion.
      map(values => Number(values.offset)),
      filter(isNonNull),
  );

  private readonly lengthBytesAndUnit$ =
      this.lengthRawBytes$.pipe(map(rawBytes => toByteUnit(rawBytes, 'long')));
  private readonly offsetBytesAndUnit$ =
      this.offsetRawBytes$.pipe(map(rawBytes => toByteUnit(rawBytes, 'long')));

  readonly lengthFormattedBytesAtUnit$ =
      this.lengthBytesAndUnit$.pipe(map(([bytes]) => bytes.toLocaleString()));
  readonly offsetFormattedBytesAtUnit$ =
      this.offsetBytesAndUnit$.pipe(map(([bytes]) => bytes.toLocaleString()));

  readonly lengthUnit$ = this.lengthBytesAndUnit$.pipe(map(([, unit]) => unit));
  readonly offsetUnit$ = this.offsetBytesAndUnit$.pipe(map(([, unit]) => unit));

  /**
   * When <length, offset>Unit$ is plain byte(s), the raw byte number and the
   * formatted byte number at <length, offset>Unit$ are equal. In this case,
   * the hint would show duplicate information. In this case, this observable
   * emits `undefined`.
   */
  readonly lengthFormattedRawBytes$ = this.lengthFormattedBytesAtUnit$.pipe(
      withLatestFrom(this.lengthRawBytes$),
      map(([formattedBytesAtUnit, rawBytes]) =>
              formatRawBytes(formattedBytesAtUnit, rawBytes)),
  );
  readonly offsetFormattedRawBytes$ = this.lengthFormattedBytesAtUnit$.pipe(
      withLatestFrom(this.offsetRawBytes$),
      map(([formattedBytesAtUnit, rawBytes]) =>
              formatRawBytes(formattedBytesAtUnit, rawBytes)),
  );

  override convertFlowArgsToFormState(flowArgs: ReadLowLevelArgs) {
    return {
      path: flowArgs.path ?? this.controls.path.defaultValue,
      length: Number(flowArgs.length ?? this.controls.length.defaultValue),
      offset: Number(flowArgs.offset ?? this.controls.offset.defaultValue),
    };
  }
}
