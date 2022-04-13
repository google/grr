import {ChangeDetectionStrategy, Component, Output} from '@angular/core';
import {UntypedFormControl, Validators} from '@angular/forms';
import {Observable} from 'rxjs';
import {filter, map, shareReplay, withLatestFrom} from 'rxjs/operators';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
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

type FormState = Omit<ReadLowLevelArgs, 'blockSize'>;

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
    FlowArgumentForm<ReadLowLevelArgs, FormState> {
  override makeControls(): Controls<FormState> {
    return {
      path: new UntypedFormControl(null, Validators.required),
      length: new UntypedFormControl(
          null, [Validators.required, Validators.min(1)]),
      offset: new UntypedFormControl(),
    };
  }

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  override convertFormStateToFlowArgs(formState: FormState): ReadLowLevelArgs {
    return {
      path: formState.path?.trim(),
      length: formState.length ?? undefined,
      offset: formState.offset ?? undefined,
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

  override convertFlowArgsToFormState(flowArgs: ReadLowLevelArgs): FormState {
    return flowArgs;
  }
}
