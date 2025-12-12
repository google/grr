import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormArray, FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';

import {
  CollectMultipleFilesArgs,
  FileFinderAccessTimeCondition,
  FileFinderContentsLiteralMatchCondition,
  FileFinderContentsRegexMatchCondition,
  FileFinderExtFlagsCondition,
  FileFinderInodeChangeTimeCondition,
  FileFinderModificationTimeCondition,
  FileFinderSizeCondition,
} from '../../../lib/api/api_interfaces';
import {
  createOptionalApiTimestampFromDate,
  createOptionalDate,
  decodeBase64ToString,
  encodeStringToBase64,
} from '../../../lib/api/translation/primitive';
import {Client} from '../../../lib/models/client';
import {FlowType} from '../../../lib/models/flow';
import {atLeastOneControlMustBeSet, FormErrors} from '../form/form_validation';
import {GlobExpressionInput} from '../form/glob_expression_form_field/glob_expression_input';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {
  createExtFlagsFormGroup,
  ExtFlagsSubform,
} from './subforms/ext_flags_subform';
import {
  createFileSizeRangeFormGroup,
  FileSizeRangeSubform,
} from './subforms/file_size_range_subform';
import {
  createLiteralMatchFormGroup,
  LiteralMatchSubform,
} from './subforms/literal_match_subform';
import {
  createRegexMatchFormGroup,
  RegexMatchSubform,
} from './subforms/regex_match_subform';
import {
  createTimeRangeFormGroup,
  TimeRangeSubform,
} from './subforms/time_range_subform';
import {SubmitButton} from './submit_button';

/** Controls for the CollectMultipleFilesForm and its descendants. */
export declare interface Controls {
  pathExpressions: FormArray<FormControl<string>>;
  modificationTime?: ReturnType<typeof createTimeRangeFormGroup>;
  accessTime?: ReturnType<typeof createTimeRangeFormGroup>;
  inodeChangeTime?: ReturnType<typeof createTimeRangeFormGroup>;
  contentsLiteralMatch?: ReturnType<typeof createLiteralMatchFormGroup>;
  contentsRegexMatch?: ReturnType<typeof createRegexMatchFormGroup>;
  size?: ReturnType<typeof createFileSizeRangeFormGroup>;
  extFlags?: ReturnType<typeof createExtFlagsFormGroup>;
}

function makeControls(): Controls {
  return {
    pathExpressions: new FormArray([new FormControl('', {nonNullable: true})], {
      validators: [atLeastOneControlMustBeSet()],
    }),
  };
}

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  styleUrls: [
    './collect_multiple_files_form.scss',
    './flow_args_form_styles.scss',
  ],
  imports: [
    CommonModule,
    ExtFlagsSubform,
    FileSizeRangeSubform,
    FormErrors,
    GlobExpressionInput,
    LiteralMatchSubform,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatRadioModule,
    ReactiveFormsModule,
    RegexMatchSubform,
    SubmitButton,
    TimeRangeSubform,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesForm extends FlowArgsFormInterface<
  CollectMultipleFilesArgs,
  Controls
> {
  readonly client = input<Client | undefined>();

  protected readonly flowType: FlowType = FlowType.COLLECT_MULTIPLE_FILES;

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): CollectMultipleFilesArgs {
    const pathExpressions = formState.pathExpressions;
    let modificationTime: FileFinderModificationTimeCondition | undefined;
    if (formState.modificationTime) {
      modificationTime = {
        minLastModifiedTime: createOptionalApiTimestampFromDate(
          formState.modificationTime.fromTime,
        ),
        maxLastModifiedTime: createOptionalApiTimestampFromDate(
          formState.modificationTime.toTime,
        ),
      };
    }
    let accessTime: FileFinderAccessTimeCondition | undefined;
    if (formState.accessTime) {
      accessTime = {
        minLastAccessTime: createOptionalApiTimestampFromDate(
          formState.accessTime.fromTime,
        ),
        maxLastAccessTime: createOptionalApiTimestampFromDate(
          formState.accessTime.toTime,
        ),
      };
    }
    let inodeChangeTime: FileFinderInodeChangeTimeCondition | undefined;
    if (formState.inodeChangeTime) {
      inodeChangeTime = {
        minLastInodeChangeTime: createOptionalApiTimestampFromDate(
          formState.inodeChangeTime.fromTime,
        ),
        maxLastInodeChangeTime: createOptionalApiTimestampFromDate(
          formState.inodeChangeTime.toTime,
        ),
      };
    }
    let contentsLiteralMatch:
      | FileFinderContentsLiteralMatchCondition
      | undefined;
    if (formState.contentsLiteralMatch) {
      contentsLiteralMatch = {
        literal: encodeStringToBase64(
          formState.contentsLiteralMatch.literal ?? '',
        ),
        mode: formState.contentsLiteralMatch.mode,
      };
    }
    let contentsRegexMatch: FileFinderContentsRegexMatchCondition | undefined;
    if (formState.contentsRegexMatch) {
      contentsRegexMatch = {
        regex: encodeStringToBase64(formState.contentsRegexMatch.regex ?? ''),
        mode: formState.contentsRegexMatch.mode,
        length: Math.floor(formState.contentsRegexMatch.length ?? 0).toString(),
      };
    }
    let size: FileFinderSizeCondition | undefined;
    if (formState.size) {
      size = {
        minFileSize: formState.size.minFileSize
          ? String(formState.size.minFileSize)
          : undefined,
        maxFileSize: formState.size.maxFileSize
          ? String(formState.size.maxFileSize)
          : undefined,
      };
    }
    let extFlags: FileFinderExtFlagsCondition | undefined;
    if (formState.extFlags) {
      extFlags = formState.extFlags;
    }
    const allResults: CollectMultipleFilesArgs = {
      pathExpressions,
      modificationTime,
      accessTime,
      inodeChangeTime,
      contentsLiteralMatch,
      contentsRegexMatch,
      size,
      extFlags,
    };

    let trimmedResults: CollectMultipleFilesArgs = {};
    for (const [argKey, argValue] of Object.entries(allResults)) {
      if (argValue != null) {
        trimmedResults = {...trimmedResults, [argKey]: argValue};
      }
    }
    return trimmedResults;
  }

  override resetFlowArgs(flowArgs: CollectMultipleFilesArgs): void {
    while (
      (flowArgs.pathExpressions?.length ?? 0) >
      this.controls.pathExpressions.length
    ) {
      // Add a new path expression as option for the user.
      this.addPathExpression();
    }

    if (flowArgs.size) {
      this.addSizeCondition();
    }
    if (flowArgs.contentsRegexMatch) {
      this.addRegexMatchCondition();
    }
    if (flowArgs.contentsLiteralMatch) {
      this.addLiteralMatchCondition();
    }
    if (flowArgs.modificationTime) {
      this.addModificationTimeCondition();
    }
    if (flowArgs.accessTime) {
      this.addAccessTimeCondition();
    }
    if (flowArgs.inodeChangeTime) {
      this.addInodeChangeTimeCondition();
    }
    if (flowArgs.extFlags) {
      this.addExtFlagsCondition();
    }

    super.resetFlowArgs(flowArgs);
  }

  override convertFlowArgsToFormState(
    flowArgs: CollectMultipleFilesArgs,
  ): ControlValues<Controls> {
    return {
      pathExpressions: flowArgs.pathExpressions?.length
        ? [...flowArgs.pathExpressions]
        : [''],
      contentsRegexMatch: {
        regex: flowArgs.contentsRegexMatch?.regex
          ? decodeBase64ToString(flowArgs.contentsRegexMatch?.regex)
          : '',
        mode: flowArgs.contentsRegexMatch?.mode,
        length: flowArgs.contentsRegexMatch?.length
          ? Number(flowArgs.contentsRegexMatch?.length)
          : undefined,
      },
      contentsLiteralMatch: {
        literal: flowArgs.contentsLiteralMatch?.literal
          ? decodeBase64ToString(flowArgs.contentsLiteralMatch?.literal)
          : '',
        mode: flowArgs.contentsLiteralMatch?.mode,
      },
      modificationTime: {
        fromTime: createOptionalDate(
          flowArgs.modificationTime?.minLastModifiedTime,
        ),
        toTime: createOptionalDate(
          flowArgs.modificationTime?.maxLastModifiedTime,
        ),
      },
      accessTime: {
        fromTime: createOptionalDate(flowArgs.accessTime?.minLastAccessTime),
        toTime: createOptionalDate(flowArgs.accessTime?.maxLastAccessTime),
      },
      inodeChangeTime: {
        fromTime: createOptionalDate(
          flowArgs.inodeChangeTime?.minLastInodeChangeTime,
        ),
        toTime: createOptionalDate(
          flowArgs.inodeChangeTime?.maxLastInodeChangeTime,
        ),
      },
      size: {
        minFileSize: flowArgs.size?.minFileSize
          ? Number(flowArgs.size.minFileSize)
          : undefined,
        maxFileSize: flowArgs.size?.maxFileSize
          ? Number(flowArgs.size.maxFileSize)
          : undefined,
      },
      extFlags: {
        linuxBitsSet: flowArgs.extFlags?.linuxBitsSet,
        linuxBitsUnset: flowArgs.extFlags?.linuxBitsUnset,
        osxBitsSet: flowArgs.extFlags?.osxBitsSet,
        osxBitsUnset: flowArgs.extFlags?.osxBitsUnset,
      },
    };
  }

  addPathExpression() {
    this.controls.pathExpressions.push(new FormControl());
  }

  removePathExpression(index: number) {
    this.controls.pathExpressions.removeAt(index);
  }

  addLiteralMatchCondition() {
    this.form.addControl('contentsLiteralMatch', createLiteralMatchFormGroup());
  }

  removeLiteralMatchCondition() {
    this.form.removeControl('contentsLiteralMatch');
  }

  addRegexMatchCondition() {
    this.form.addControl('contentsRegexMatch', createRegexMatchFormGroup());
  }

  removeRegexMatchCondition() {
    this.form.removeControl('contentsRegexMatch');
  }

  addModificationTimeCondition() {
    this.form.addControl('modificationTime', createTimeRangeFormGroup());
  }

  removeModificationTimeCondition() {
    this.form.removeControl('modificationTime');
  }

  addAccessTimeCondition() {
    this.form.addControl('accessTime', createTimeRangeFormGroup());
  }

  removeAccessTimeCondition() {
    this.form.removeControl('accessTime');
  }

  addInodeChangeTimeCondition() {
    this.form.addControl('inodeChangeTime', createTimeRangeFormGroup());
  }

  removeInodeChangeTimeCondition() {
    this.form.removeControl('inodeChangeTime');
  }

  addSizeCondition() {
    this.form.addControl('size', createFileSizeRangeFormGroup());
  }

  removeSizeCondition() {
    this.form.removeControl('size');
  }

  addExtFlagsCondition() {
    this.form.addControl('extFlags', createExtFlagsFormGroup());
  }

  removeExtFlagsCondition() {
    this.form.removeControl('extFlags');
  }
}
