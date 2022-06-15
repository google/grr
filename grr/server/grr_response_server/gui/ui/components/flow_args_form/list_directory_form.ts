import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListDirectoryArgs, PathSpecPathType} from '../../lib/api/api_interfaces';

const COLLECTION_METHODS: ReadonlyArray<PathSpecPathType> =
    [PathSpecPathType.OS, PathSpecPathType.TSK, PathSpecPathType.NTFS];

function makeControls() {
  return {
    collectionMethod: new FormControl(PathSpecPathType.OS, {nonNullable: true}),
    path: new FormControl('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;


/**
 * A form that makes it possible to configure the list directory flow.
 */
@Component({
  selector: 'list-directory-form',
  templateUrl: './list_directory_form.ng.html',
  styleUrls: ['./list_directory_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ListDirectoryForm extends
    FlowArgumentForm<ListDirectoryArgs, Controls> {
  readonly collectionMethods = COLLECTION_METHODS;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: ListDirectoryArgs) {
    return {
      collectionMethod: flowArgs.pathspec?.pathtype ??
          this.controls.collectionMethod.defaultValue,
      path: flowArgs.pathspec?.path ?? this.controls.path.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      pathspec: {
        pathtype: formState.collectionMethod,
        path: formState.path,
      },
    };
  }
}
