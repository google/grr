import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';

import {
  CollectFilesByKnownPathArgs,
  CollectFilesByKnownPathArgsCollectionLevel,
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

interface CollectionLevel {
  readonly value: CollectFilesByKnownPathArgsCollectionLevel;
  readonly label: string;
}

const COLLECTION_LEVELS: readonly CollectionLevel[] = [
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    label: 'Collect entire file(s) (stat & hash included)',
  },
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.HASH,
    label: 'Collect file(s) hash(es) (stat included)',
  },
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.STAT,
    label: 'Collect file(s) stat',
  },
];

function makeControls() {
  return {
    paths: new FormControlWithWarnings('', {
      nonNullable: true,
      validators: [
        requiredInput(),
        literalGlobExpressionWarning(),
        literalKnowledgebaseExpressionWarning(),
      ],
    }),
    collectionLevel: new FormControl(
      CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
      {nonNullable: true},
    ),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the CollectFilesByKnownPath
 * flow.
 */
@Component({
  selector: 'collect-files-by-known-path-form',
  templateUrl: './collect_files_by_known_path_form.ng.html',
  styleUrls: [
    'flow_args_form_styles.scss',
    './collect_files_by_known_path_form.scss',
  ],
  imports: [
    CommonModule,
    FormErrors,
    FormWarnings,
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
export class CollectFilesByKnownPathForm extends FlowArgsFormInterface<
  CollectFilesByKnownPathArgs,
  Controls
> {
  readonly COLLECTION_LEVELS = COLLECTION_LEVELS;
  showAdvancedParams = false;

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): CollectFilesByKnownPathArgs {
    return {
      paths: formState.paths
        ?.split('\n')
        .map((path: string) => path.trim())
        .filter((path: string) => path !== ''),
      collectionLevel: formState.collectionLevel,
    };
  }

  override convertFlowArgsToFormState(
    flowArgs: CollectFilesByKnownPathArgs,
  ): ControlValues<Controls> {
    return {
      paths: flowArgs.paths?.join('\n') ?? this.controls.paths.defaultValue,
      collectionLevel:
        flowArgs.collectionLevel ?? this.controls.collectionLevel.defaultValue,
    };
  }
}
