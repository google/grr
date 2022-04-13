import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListDirectoryArgs, PathSpecPathType} from '../../lib/api/api_interfaces';

const COLLECTION_METHODS: ReadonlyArray<PathSpecPathType> =
    [PathSpecPathType.OS, PathSpecPathType.TSK, PathSpecPathType.NTFS];

declare interface FormState {
  path: string;
  collectionMethod: PathSpecPathType;
}

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
    FlowArgumentForm<ListDirectoryArgs, FormState> {
  readonly collectionMethods = COLLECTION_METHODS;

  override makeControls(): Controls<FormState> {
    return {
      collectionMethod: new UntypedFormControl(),
      path: new UntypedFormControl(),
    };
  }

  override convertFlowArgsToFormState(flowArgs: ListDirectoryArgs): FormState {
    return {
      collectionMethod: flowArgs.pathspec?.pathtype ?? PathSpecPathType.OS,
      path: flowArgs.pathspec?.path ?? '',
    };
  }

  override convertFormStateToFlowArgs(formState: FormState): ListDirectoryArgs {
    return {
      pathspec: {
        pathtype: formState.collectionMethod,
        path: formState.path,
      },
    };
  }
}
