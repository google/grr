import {ChangeDetectionStrategy, Component} from '@angular/core';
import {AbstractControl, UntypedFormArray, UntypedFormControl, UntypedFormGroup, ValidationErrors} from '@angular/forms';

import {ExtFlagsCondition} from '../../components/flow_args_form/collect_multiple_files_form_helpers/ext_flags_condition';
import {createLiteralMatchFormGroup, formValuesToFileFinderContentsLiteralMatchCondition, LiteralMatchRawFormValues} from '../../components/flow_args_form/collect_multiple_files_form_helpers/literal_match_condition';
import {createRegexMatchFormGroup, formValuesToFileFinderContentsRegexMatchCondition, RegexMatchRawFormValues} from '../../components/flow_args_form/collect_multiple_files_form_helpers/regex_match_condition';
import {createSizeFormGroup} from '../../components/flow_args_form/collect_multiple_files_form_helpers/size_condition';
import {createTimeRangeFormGroup, formValuesToFileFinderAccessTimeCondition, formValuesToFileFinderInodeChangeTimeCondition, formValuesToFileFinderModificationTimeCondition, RawFormValues} from '../../components/flow_args_form/collect_multiple_files_form_helpers/time_range_condition';
import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {CollectMultipleFilesArgs, FileFinderSizeCondition} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';


function atLeastOnePathExpression(control: AbstractControl): ValidationErrors {
  for (const c of (control as UntypedFormArray).controls) {
    if (isNonNull(c.value) && c.value.trim() !== '') {
      return {};
    }
  }

  return {
    'atLeastOnePathExpressionExpected': true,
  };
}

declare interface MinFormState {
  pathExpressions: ReadonlyArray<string>;
}

declare interface FullFormState extends MinFormState {
  modificationTime?: RawFormValues;
  accessTime?: RawFormValues;
  inodeChangeTime?: RawFormValues;
  contentsLiteralMatch?: LiteralMatchRawFormValues;
  contentsRegexMatch?: RegexMatchRawFormValues;
  size?: FileFinderSizeCondition;
  extFlags?: {};
}

declare interface MinControls {
  pathExpressions: UntypedFormArray;
}

declare interface FullControls extends MinControls {
  modificationTime?: UntypedFormGroup;
  accessTime?: UntypedFormGroup;
  inodeChangeTime?: UntypedFormGroup;
  contentsLiteralMatch?: UntypedFormGroup;
  contentsRegexMatch?: UntypedFormGroup;
  size?: UntypedFormGroup;
  extFlags?: UntypedFormGroup;
}

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  styleUrls: ['./collect_multiple_files_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class CollectMultipleFilesForm extends
    FlowArgumentForm<CollectMultipleFilesArgs, MinFormState, MinControls> {
  override makeControls(): MinControls {
    return {
      pathExpressions: new UntypedFormArray(
          [new UntypedFormControl()], atLeastOnePathExpression),
    };
  }

  get fullControls() {
    return this.controls as FullControls;
  }

  override convertFormStateToFlowArgs(formState: FullFormState):
      CollectMultipleFilesArgs {
    const allResults: CollectMultipleFilesArgs = {
      pathExpressions: formState.pathExpressions,
      modificationTime: formState.modificationTime &&
          formValuesToFileFinderModificationTimeCondition(
                            formState.modificationTime),
      accessTime: formState.accessTime &&
          formValuesToFileFinderAccessTimeCondition(formState.accessTime),
      inodeChangeTime: formState.inodeChangeTime &&
          formValuesToFileFinderInodeChangeTimeCondition(
                           formState.inodeChangeTime),
      contentsLiteralMatch: formState.contentsLiteralMatch &&
          formValuesToFileFinderContentsLiteralMatchCondition(
                                formState.contentsLiteralMatch),
      contentsRegexMatch: formState.contentsRegexMatch &&
          formValuesToFileFinderContentsRegexMatchCondition(
                              formState.contentsRegexMatch),
      size: formState.size as FileFinderSizeCondition,
      extFlags: formState.extFlags,
    };

    let trimmedResults: CollectMultipleFilesArgs = {};
    for (const [argKey, argValue] of Object.entries(allResults)) {
      if (argValue != null) {
        trimmedResults = {...trimmedResults, [argKey]: argValue};
      }
    }
    return trimmedResults;
  }

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  constructor(
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
  ) {
    super();
  }

  override resetFlowArgs(flowArgs: CollectMultipleFilesArgs): void {
    while ((flowArgs.pathExpressions?.length ?? 0) >
           this.controls.pathExpressions.length) {
      this.addPathExpression();
    }
    super.resetFlowArgs(flowArgs);
    // TODO: Add flow condition controls if present.
  }

  override convertFlowArgsToFormState(flowArgs: CollectMultipleFilesArgs):
      FullFormState {
    const pathExpressions =
        flowArgs.pathExpressions?.length ? flowArgs.pathExpressions : [''];

    return {
      // TODO: Add flow condition controls if present.
      pathExpressions,
    };
  }

  addPathExpression() {
    this.controls.pathExpressions.push(new UntypedFormControl());
  }

  removePathExpression(index: number) {
    this.controls.pathExpressions.removeAt(index);
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
    this.form.addControl('size', createSizeFormGroup());
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
