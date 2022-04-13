import {ChangeDetectionStrategy, Component} from '@angular/core';
import {AbstractControl, UntypedFormControl, ValidationErrors} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectFilesByKnownPathArgs, CollectFilesByKnownPathArgsCollectionLevel} from '../../lib/api/api_interfaces';


interface CollectionLevel {
  readonly value: CollectFilesByKnownPathArgsCollectionLevel;
  readonly label: string;
}

const COLLECTION_LEVELS: ReadonlyArray<CollectionLevel> = [
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    label: 'Collect entire file(s) (stat & hash included)'
  },
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.HASH,
    label: 'Collect file(s) hash(es) (stat included)'
  },
  {
    value: CollectFilesByKnownPathArgsCollectionLevel.STAT,
    label: 'Collect file(s) stat'
  },
];

function atLeastOnePath(control: AbstractControl): ValidationErrors {
  if ((control.value ?? '').trim()) return {};

  return {
    'atLeastOnePathExpected': true,
  };
}

declare interface FormState {
  paths: string;
  collectionLevel: CollectFilesByKnownPathArgsCollectionLevel;
}

/**
 * A form that makes it possible to configure the CollectFilesByKnownPath
 * flow.
 */
@Component({
  selector: 'collect-files-by-known-path-form',
  templateUrl: './collect_files_by_known_path_form.ng.html',
  styleUrls: ['./collect_files_by_known_path_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class CollectFilesByKnownPathForm extends
    FlowArgumentForm<CollectFilesByKnownPathArgs, FormState> {
  readonly collectionLevels = COLLECTION_LEVELS;

  hideAdvancedParams = true;

  override makeControls(): Controls<FormState> {
    return {
      paths: new UntypedFormControl('', atLeastOnePath),
      collectionLevel: new UntypedFormControl(
          CollectFilesByKnownPathArgsCollectionLevel.CONTENT),
    };
  }


  override convertFormStateToFlowArgs(formState: FormState) {
    return {
      paths: formState.paths?.split('\n')
                 .map(path => path.trim())
                 .filter(path => path !== ''),
      collectionLevel: formState.collectionLevel,
    };
  }

  override convertFlowArgsToFormState(flowArgs: CollectFilesByKnownPathArgs):
      FormState {
    return {
      paths: flowArgs.paths?.join('\n') ?? '',
      collectionLevel: flowArgs.collectionLevel ??
          CollectFilesByKnownPathArgsCollectionLevel.CONTENT
    };
  }

  toggleAdvancedParams() {
    this.hideAdvancedParams = !this.hideAdvancedParams;
  }
}
