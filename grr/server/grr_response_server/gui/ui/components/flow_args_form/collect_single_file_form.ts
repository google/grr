import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';
import {Observable} from 'rxjs';
import {filter, map, shareReplay, withLatestFrom} from 'rxjs/operators';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectSingleFileArgs} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {toByteUnit} from '../form/byte_input/byte_conversion';

function makeControls() {
  return {
    path: new FormControl('', {nonNullable: true}),
    maxSizeBytes: new FormControl<number|undefined>(undefined, {
      nonNullable: true,
      validators: [Validators.required],
    }),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a CollectSingleFile flow. */
@Component({
  selector: 'collect-single-file-form',
  templateUrl: './collect_single_file_form.ng.html',
  styleUrls: ['./collect_single_file_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class CollectSingleFileForm extends
    FlowArgumentForm<CollectSingleFileArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  private readonly rawBytes$: Observable<number> =
      this.controls.maxSizeBytes.valueChanges.pipe(
          filter(isNonNull), shareReplay(1));

  private readonly bytesAndUnit$ =
      this.rawBytes$.pipe(map(rawBytes => toByteUnit(rawBytes, 'long')));

  readonly formattedBytesAtUnit$ = this.bytesAndUnit$.pipe(
      map(([bytes]) => bytes.toLocaleString()),
  );

  readonly unit$ = this.bytesAndUnit$.pipe(map(([, unit]) => unit));

  /**
   * When unit$ is plain byte(s), the raw byte number and the formatted byte
   * number at unit$ are equal. In this case, the hint would show duplicate
   * information. In this case, this observable emits `undefined`.
   */
  readonly formattedRawBytes$ = this.formattedBytesAtUnit$.pipe(
      withLatestFrom(this.rawBytes$),
      map(([formattedBytesAtUnit, rawBytes]) => {
        const formattedRawBytes = rawBytes.toLocaleString();
        if (formattedBytesAtUnit === formattedRawBytes) {
          return undefined;
        } else {
          return formattedRawBytes;
        }
      }),
  );

  override convertFlowArgsToFormState(flowArgs: CollectSingleFileArgs) {
    return {
      path: flowArgs.path ?? '',
      maxSizeBytes: flowArgs.maxSizeBytes ? Number(flowArgs.maxSizeBytes) :
                                            undefined,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      path: formState.path,
      maxSizeBytes: formState.maxSizeBytes?.toString(),
    };
  }
}
