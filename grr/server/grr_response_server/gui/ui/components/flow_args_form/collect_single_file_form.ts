import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {Observable} from 'rxjs';
import {filter, map, shareReplay, withLatestFrom} from 'rxjs/operators';

import {CollectSingleFileArgs} from '../../lib/api/api_interfaces';
import {toByteUnit} from '../form/byte_input/byte_conversion';

/** Form that configures a CollectSingleFile flow. */
@Component({
  selector: 'collect-single-file-form',
  templateUrl: './collect_single_file_form.ng.html',
  styleUrls: ['./collect_single_file_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectSingleFileForm extends
    FlowArgumentForm<CollectSingleFileArgs> implements OnInit {
  readonly form = new FormGroup({
    path: new FormControl(),
    maxSizeBytes: new FormControl(null, Validators.required),
  });

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  private readonly rawBytes$: Observable<number> = this.formValues$.pipe(
      map(values => values.maxSizeBytes),
      filter(size => size !== undefined && size !== null),
  );

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

  ngOnInit() {
    this.form.patchValue({
      path: this.defaultFlowArgs.path,
      maxSizeBytes: this.defaultFlowArgs.maxSizeBytes ?
          Number(this.defaultFlowArgs.maxSizeBytes) :
          undefined,
    });
  }
}
