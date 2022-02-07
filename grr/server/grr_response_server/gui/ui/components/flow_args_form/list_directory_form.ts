import {Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {map, shareReplay} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListDirectoryArgs, PathSpecPathType} from '../../lib/api/api_interfaces';

const COLLECTION_METHODS: ReadonlyArray<PathSpecPathType> =
    [PathSpecPathType.OS, PathSpecPathType.TSK, PathSpecPathType.NTFS];

/**
 * A form that makes it possible to configure the list directory flow.
 */
@Component({
  selector: 'list-directory-form',
  templateUrl: './list_directory_form.ng.html',
  styleUrls: ['./list_directory_form.scss'],
})
export class ListDirectoryForm extends
    FlowArgumentForm<ListDirectoryArgs> implements OnInit {
  readonly collectionMethods = COLLECTION_METHODS;

  readonly controls = {
    collectionMethod: new FormControl(),
    path: new FormControl(),
  };
  readonly form = new FormGroup(this.controls);

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map((v) => {
        return {pathspec: {pathtype: v.collectionMethod, path: v.path}};
      }),
      shareReplay(1));

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  ngOnInit() {
    this.form.patchValue({
      collectionMethod: this.defaultFlowArgs?.pathspec?.pathtype,
      path: this.defaultFlowArgs?.pathspec?.path,
    });
  }
}
