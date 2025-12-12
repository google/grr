import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatRadioModule} from '@angular/material/radio';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';

import {
  ListDirectoryArgs,
  PathSpecPathType,
} from '../../../lib/api/api_interfaces';
import {
  FormControlWithWarnings,
  FormErrors,
  FormWarnings,
  literalGlobExpressionWarning,
  literalKnowledgebaseExpressionWarning,
  requiredInput,
} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

const COLLECTION_METHODS: readonly PathSpecPathType[] = [
  PathSpecPathType.OS,
  PathSpecPathType.TSK,
  PathSpecPathType.NTFS,
];

function makeControls() {
  return {
    collectionMethod: new FormControl(PathSpecPathType.OS, {nonNullable: true}),
    path: new FormControlWithWarnings('', {
      nonNullable: true,
      validators: [
        requiredInput(),
        literalGlobExpressionWarning(),
        literalKnowledgebaseExpressionWarning(),
      ],
    }),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the list directory flow.
 */
@Component({
  selector: 'list-directory-form',
  templateUrl: './list_directory_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    FormsModule,
    FormWarnings,
    MatAutocompleteModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatRadioModule,
    MatSelectModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListDirectoryForm extends FlowArgsFormInterface<
  ListDirectoryArgs,
  Controls
> {
  readonly collectionMethods = COLLECTION_METHODS;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ListDirectoryArgs,
  ): ControlValues<Controls> {
    return {
      collectionMethod:
        flowArgs.pathspec?.pathtype ??
        this.controls.collectionMethod.defaultValue,
      path: flowArgs.pathspec?.path ?? this.controls.path.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ListDirectoryArgs {
    return {
      pathspec: {
        pathtype: formState.collectionMethod,
        path: formState.path,
      },
    };
  }
}
