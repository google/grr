import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {AbstractControl, FormArray, FormControl, FormGroup, ValidationErrors} from '@angular/forms';
import {ExtFlagsCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/ext_flags_condition';
import {createLiteralMatchFormGroup} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/literal_match_condition';
import {createRegexMatchFormGroup, formValuesToFileFinderContentsRegexMatchCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/regex_match_condition';
import {SizeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/size_condition';
import {createTimeRangeFormGroup, formValuesToFileFinderAccessTimeCondition, formValuesToFileFinderInodeChangeTimeCondition, formValuesToFileFinderModificationTimeCondition} from '@app/components/flow_args_form/collect_multiple_files_form_helpers/time_range_condition';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {isNonNull} from '@app/lib/preconditions';
import {filter, map, shareReplay} from 'rxjs/operators';

import {CollectMultipleFilesArgs, FileFinderContentsLiteralMatchCondition} from '../../lib/api/api_interfaces';
import {ClientPageFacade} from '../../store/client_page_facade';


function atLeastOnePathExpression(control: AbstractControl): ValidationErrors {
  for (const c of (control as FormArray).controls) {
    if (isNonNull(c.value) && c.value.trim() !== '') {
      return {};
    }
  }

  return {
    'atLeastOnePathExpressionExpected': true,
  };
}

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
    pathExpressions: new FormArray([], atLeastOnePathExpression),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      filter(isNonNull),
      map(v => {
        const allResults: CollectMultipleFilesArgs = {
          pathExpressions: v.pathExpressions,
          modificationTime: v.modificationTime &&
              formValuesToFileFinderModificationTimeCondition(
                                v.modificationTime),
          accessTime: v.accessTime &&
              formValuesToFileFinderAccessTimeCondition(v.accessTime),
          inodeChangeTime: v.inodeChangeTime &&
              formValuesToFileFinderInodeChangeTimeCondition(v.inodeChangeTime),
          contentsLiteralMatch: v.contentsLiteralMatch as
              FileFinderContentsLiteralMatchCondition,
          contentsRegexMatch: v.contentsRegexMatch &&
              formValuesToFileFinderContentsRegexMatchCondition(
                                  v.contentsRegexMatch),
        };

        let trimmedResults: CollectMultipleFilesArgs = {};
        for (const [argKey, argValue] of Object.entries(allResults)) {
          if (argValue != null) {
            trimmedResults = {...trimmedResults, [argKey]: argValue};
          }
        }
        return trimmedResults;
      }),
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
    this.form.addControl('contentsLiteralMatch', createLiteralMatchFormGroup());
  }

  removeLiteralMatchCondition() {
    this.form.removeControl('contentsLiteralMatch');
  }

  // Regex match condition.
  addRegexMatchCondition() {
    this.form.addControl('contentsRegexMatch', createRegexMatchFormGroup());
  }

  removeRegexMatchCondition() {
    this.form.removeControl('contentsRegexMatch');
  }

  // Modification time condition.
  addModificationTimeCondition() {
    this.form.addControl('modificationTime', createTimeRangeFormGroup());
  }

  removeModificationTimeCondition() {
    this.form.removeControl('modificationTime');
  }

  // Access time condition.
  addAccessTimeCondition() {
    this.form.addControl('accessTime', createTimeRangeFormGroup());
  }

  removeAccessTimeCondition() {
    this.form.removeControl('accessTime');
  }

  // Inode change time condition.
  addInodeChangeTimeCondition() {
    this.form.addControl('inodeChangeTime', createTimeRangeFormGroup());
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
