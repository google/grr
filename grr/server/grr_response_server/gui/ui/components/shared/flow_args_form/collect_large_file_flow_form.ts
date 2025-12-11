import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';

import {
  CollectLargeFileFlowArgs,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {FormErrors, requiredInput} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

const PATHTYPES: readonly PathSpecPathType[] = [
  PathSpecPathType.OS,
  PathSpecPathType.TSK,
  PathSpecPathType.NTFS,
];

function makeControls() {
  return {
    path: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    signedUrl: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    pathtype: new FormControl(PathSpecPathType.OS, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the CollectFilesByKnownPath
 * flow.
 */
@Component({
  selector: 'collect-large-file-flow-form',
  templateUrl: './collect_large_file_flow_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatRadioModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectLargeFileFlowForm extends FlowArgsFormInterface<
  CollectLargeFileFlowArgs,
  Controls
> {
  readonly pathtypes = PATHTYPES;

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): CollectLargeFileFlowArgs {
    return {
      pathSpec: {
        path: formState.path.trim() ?? '',
        pathtype: formState.pathtype,
      },
      signedUrl: formState.signedUrl?.trim() ?? '',
    };
  }

  override convertFlowArgsToFormState(
    flowArgs: CollectLargeFileFlowArgs,
  ): ControlValues<Controls> {
    return {
      path: flowArgs.pathSpec?.path ?? this.controls.path.defaultValue,
      signedUrl: flowArgs.signedUrl ?? this.controls.signedUrl.defaultValue,
      pathtype:
        flowArgs.pathSpec?.pathtype ?? this.controls.pathtype.defaultValue,
    };
  }
}
