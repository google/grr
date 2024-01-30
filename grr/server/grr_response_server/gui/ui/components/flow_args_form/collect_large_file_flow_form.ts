import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';

import {
  ControlValues,
  FlowArgumentForm,
} from '../../components/flow_args_form/form_interface';
import {
  CollectLargeFileFlowArgs,
  PathSpecPathType,
} from '../../lib/api/api_interfaces';

const PATH_TYPES: readonly PathSpecPathType[] = [
  PathSpecPathType.OS,
  PathSpecPathType.TSK,
  PathSpecPathType.NTFS,
];

function makeControls() {
  return {
    path: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    signedUrl: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    pathType: new FormControl(PathSpecPathType.OS, {nonNullable: true}),
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
  styleUrls: ['./collect_large_file_flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectLargeFileFlowForm extends FlowArgumentForm<
  CollectLargeFileFlowArgs,
  Controls
> {
  readonly pathTypes = PATH_TYPES;

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      pathSpec: {
        path: formState.path.trim() ?? '',
        pathtype: formState.pathType,
      },
      signedUrl: formState.signedUrl?.trim() ?? '',
    };
  }

  override convertFlowArgsToFormState(flowArgs: CollectLargeFileFlowArgs) {
    return {
      path: flowArgs.pathSpec?.path ?? this.controls.path.defaultValue,
      signedUrl: flowArgs.signedUrl ?? this.controls.signedUrl.defaultValue,
      pathType:
        flowArgs.pathSpec?.pathtype ?? this.controls.pathType.defaultValue,
    };
  }
}
