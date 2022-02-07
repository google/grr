import {Component, OnInit, Output} from '@angular/core';
import {AbstractControl, FormControl, FormGroup, ValidationErrors} from '@angular/forms';
import {filter, map, shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectFilesByKnownPathArgs, CollectFilesByKnownPathArgsCollectionLevel} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';

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

/**
 * A form that makes it possible to configure the CollectFilesByKnownPath
 * flow.
 */
@Component({
  selector: 'collect-files-by-known-path-form',
  templateUrl: './collect_files_by_known_path_form.ng.html',
  styleUrls: ['./collect_files_by_known_path_form.scss'],
})
export class CollectFilesByKnownPathForm extends
    FlowArgumentForm<CollectFilesByKnownPathArgs> implements OnInit {
  readonly collectionLevels = COLLECTION_LEVELS;

  hideAdvancedParams = true;

  readonly controls = {
    paths: new FormControl('', atLeastOnePath),
    collectionLevel:
        new FormControl(CollectFilesByKnownPathArgsCollectionLevel.CONTENT),
  };
  readonly form = new FormGroup(this.controls);

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      filter(isNonNull),
      map(v => {
        const allPaths: string[] = v.paths.split('\n');
        const trimmedPaths: string[] = [];
        for (const path of allPaths) {
          if ((path ?? '').trim() !== '') {
            trimmedPaths.push(path.trim());
          }
        }
        const args: CollectFilesByKnownPathArgs = {
          paths: trimmedPaths,
          collectionLevel: v.collectionLevel
        };
        return args;
      }),
      shareReplay({bufferSize: 1, refCount: true}),
  );

  @Output()
  readonly status$ = this.form.statusChanges.pipe(
      shareReplay({bufferSize: 1, refCount: true}));

  ngOnInit() {
    this.form.patchValue({
      paths: this.defaultFlowArgs?.paths?.join('\n') ?? '',
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT
    });
  }

  toggleAdvancedParams() {
    this.hideAdvancedParams = !this.hideAdvancedParams;
  }
}
