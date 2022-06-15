import {ChangeDetectionStrategy, Component} from '@angular/core';
import {AbstractControl, FormControl, ValidationErrors} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
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

function makeControls() {
  return {
    paths:
        new FormControl('', {nonNullable: true, validators: [atLeastOnePath]}),
    collectionLevel: new FormControl(
        CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
        {nonNullable: true}),
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
  styleUrls: ['./collect_files_by_known_path_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class CollectFilesByKnownPathForm extends
    FlowArgumentForm<CollectFilesByKnownPathArgs, Controls> {
  readonly collectionLevels = COLLECTION_LEVELS;

  hideAdvancedParams = true;

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      paths: formState.paths?.split('\n')
                 .map(path => path.trim())
                 .filter(path => path !== ''),
      collectionLevel: formState.collectionLevel,
    };
  }

  override convertFlowArgsToFormState(flowArgs: CollectFilesByKnownPathArgs) {
    return {
      paths: flowArgs.paths?.join('\n') ?? this.controls.paths.defaultValue,
      collectionLevel: flowArgs.collectionLevel ??
          this.controls.collectionLevel.defaultValue,
    };
  }

  toggleAdvancedParams() {
    this.hideAdvancedParams = !this.hideAdvancedParams;
  }
}
