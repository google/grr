import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormArray, FormControl, FormGroup} from '@angular/forms';
import {AccessTimeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/access_time_condition';
import {ExtFlagsCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/ext_flags_condition';
import {InodeChangeTimeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/inode_change_time_condition';
import {LiteralMatchCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/literal_match_condition';
import {ModificationTimeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/modification_time_condition';
import {RegexMatchCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/regex_match_condition';
import {SizeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/size_condition';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {map, shareReplay} from 'rxjs/operators';

import {CollectMultipleFilesArgs} from '../../lib/api/api_interfaces';
import {ClientPageFacade} from '../../store/client_page_facade';

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  styleUrls: ['./collect_multiple_files_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesForm extends
    FlowArgumentForm<CollectMultipleFilesArgs> implements OnInit {
  readonly form = new FormGroup({
    pathExpressions: new FormArray([]),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      shareReplay(1),
  );

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  readonly clientId$ = this.clientPageFacade.selectedClient$.pipe(
      map(client => client?.clientId),
  );

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
  ) {
    super();
  }

  ngOnInit() {
    const pathExpressions = this.defaultFlowArgs.pathExpressions?.length ?
        this.defaultFlowArgs.pathExpressions :
        [''];

    pathExpressions.forEach(() => {
      this.addPathExpression();
    });

    this.form.patchValue({pathExpressions});
  }

  get pathExpressions(): FormArray {
    return this.form.get('pathExpressions') as FormArray;
  }

  addPathExpression() {
    this.pathExpressions.push(new FormControl());
  }

  removePathExpression(index: number) {
    this.pathExpressions.removeAt(index);
  }

  // Literal match condition.
  addLiteralMatchCondition() {
    this.form.addControl(
        'contentsLiteralMatch', LiteralMatchCondition.createFormGroup());
  }

  removeLiteralMatchCondition() {
    this.form.removeControl('contentsLiteralMatch');
  }

  // Regex match condition.
  addRegexMatchCondition() {
    this.form.addControl(
        'contentsRegexMatch', RegexMatchCondition.createFormGroup());
  }

  removeRegexMatchCondition() {
    this.form.removeControl('contentsRegexMatch');
  }

  // Modification time condition.
  addModificationTimeCondition() {
    this.form.addControl(
        'modificationTime', ModificationTimeCondition.createFormGroup());
  }

  removeModificationTimeCondition() {
    this.form.removeControl('modificationTime');
  }

  // Access time condition.
  addAccessTimeCondition() {
    this.form.addControl('accessTime', AccessTimeCondition.createFormGroup());
  }

  removeAccessTimeCondition() {
    this.form.removeControl('accessTime');
  }

  // Inode change time condition.
  addInodeChangeTimeCondition() {
    this.form.addControl(
        'inodeChangeTime', InodeChangeTimeCondition.createFormGroup());
  }

  removeInodeChangeTimeCondition() {
    this.form.removeControl('inodeChangeTime');
  }

  // File size condition.
  addSizeCondition() {
    this.form.addControl('size', SizeCondition.createFormGroup());
  }

  removeSizeCondition() {
    this.form.removeControl('size');
  }

  // Extended file flags condition.
  addExtFlagsCondition() {
    this.form.addControl('extFlags', ExtFlagsCondition.createFormGroup());
  }

  removeExtFlagsCondition() {
    this.form.removeControl('extFlags');
  }
}
