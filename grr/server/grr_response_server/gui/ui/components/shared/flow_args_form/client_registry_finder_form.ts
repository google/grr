import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {FormArray, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';

import {
  FileFinderContentsLiteralMatchCondition,
  FileFinderContentsRegexMatchCondition,
  FileFinderModificationTimeCondition,
  FileFinderSizeCondition,
  RegistryFinderArgs,
  RegistryFinderCondition,
  RegistryFinderConditionType,
} from '../../../lib/api/api_interfaces';
import {
  createOptionalApiTimestampFromDate,
  createOptionalDate,
  decodeBase64ToString,
  encodeStringToBase64,
} from '../../../lib/api/translation/primitive';
import {Client} from '../../../lib/models/client';
import {
  atLeastOneControlMustBeSet,
  FormControlWithWarnings,
  FormErrors,
  FormWarnings,
  windowsPathWarning,
} from '../form/form_validation';
import {GlobExpressionInput} from '../form/glob_expression_form_field/glob_expression_input';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
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

/** Controls for the ClientRegistryFinderForm and its descendants. */
export declare interface Controls {
  keysPaths: FormArray<FormControlWithWarnings>;
  modificationTimes: FormArray<ReturnType<typeof createTimeRangeFormGroup>>;
  valueLiteralMatches: FormArray<
    ReturnType<typeof createLiteralMatchFormGroup>
  >;
  valueRegexMatches: FormArray<ReturnType<typeof createRegexMatchFormGroup>>;
  sizes: FormArray<ReturnType<typeof createFileSizeRangeFormGroup>>;
}

function makeControls(): Controls {
  return {
    keysPaths: new FormArray(
      [
        new FormControlWithWarnings('', {
          nonNullable: true,
          validators: [windowsPathWarning()],
        }),
      ],
      {
        validators: [atLeastOneControlMustBeSet()],
      },
    ),
    modificationTimes: new FormArray<
      ReturnType<typeof createTimeRangeFormGroup>
    >([]),
    valueLiteralMatches: new FormArray<
      ReturnType<typeof createLiteralMatchFormGroup>
    >([]),
    valueRegexMatches: new FormArray<
      ReturnType<typeof createRegexMatchFormGroup>
    >([]),
    sizes: new FormArray<ReturnType<typeof createFileSizeRangeFormGroup>>([]),
  };
}

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'client-registry-finder-form',
  templateUrl: './client_registry_finder_form.ng.html',
  styleUrls: [
    './flow_args_form_styles.scss',
    './client_registry_finder_form.scss',
  ],
  imports: [
    CommonModule,
    FileSizeRangeSubform,
    FormErrors,
    FormWarnings,
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
export class ClientRegistryFinderForm extends FlowArgsFormInterface<
  RegistryFinderArgs,
  Controls
> {
  readonly client = input<Client | undefined>();

  override makeControls() {
    return makeControls();
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): RegistryFinderArgs {
    const keysPaths = formState.keysPaths.filter((path) => path !== '');
    const conditions: RegistryFinderCondition[] = [];

    for (const condition of formState.valueLiteralMatches ?? []) {
      if (condition) {
        const valueLiteralMatch: FileFinderContentsLiteralMatchCondition = {
          literal: encodeStringToBase64(condition.literal ?? ''),
          mode: condition.mode,
        };
        conditions.push({
          conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
          valueLiteralMatch,
        });
      }
    }
    for (const condition of formState.valueRegexMatches ?? []) {
      if (condition) {
        const valueRegexMatch: FileFinderContentsRegexMatchCondition = {
          regex: encodeStringToBase64(condition.regex ?? ''),
          mode: condition.mode,
          length: Math.floor(condition.length ?? 0).toString(),
        };
        conditions.push({
          conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
          valueRegexMatch,
        });
      }
    }
    for (const condition of formState.modificationTimes ?? []) {
      if (condition) {
        const modificationTime: FileFinderModificationTimeCondition = {
          minLastModifiedTime: createOptionalApiTimestampFromDate(
            condition.fromTime,
          ),
          maxLastModifiedTime: createOptionalApiTimestampFromDate(
            condition.toTime,
          ),
        };
        conditions.push({
          conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
          modificationTime,
        });
      }
    }
    for (const condition of formState.sizes ?? []) {
      if (condition) {
        const size: FileFinderSizeCondition = {
          minFileSize: condition.minFileSize
            ? String(condition.minFileSize)
            : undefined,
          maxFileSize: condition.maxFileSize
            ? String(condition.maxFileSize)
            : undefined,
        };
        conditions.push({
          conditionType: RegistryFinderConditionType.SIZE,
          size,
        });
      }
    }

    return {
      keysPaths,
      conditions,
    };
  }

  override resetFlowArgs(flowArgs: RegistryFinderArgs): void {
    while ((flowArgs.keysPaths?.length ?? 0) > this.controls.keysPaths.length) {
      // Add a new path expression as option for the user.
      this.addKeysPathExpression();
    }
    for (const condition of flowArgs.conditions ?? []) {
      if (
        condition.conditionType ===
          RegistryFinderConditionType.MODIFICATION_TIME &&
        condition.modificationTime != null
      ) {
        this.addModificationTimeCondition();
      }
      if (
        condition.conditionType ===
          RegistryFinderConditionType.VALUE_LITERAL_MATCH &&
        condition.valueLiteralMatch != null
      ) {
        this.addLiteralMatchCondition();
      }
      if (
        condition.conditionType ===
          RegistryFinderConditionType.VALUE_REGEX_MATCH &&
        condition.valueRegexMatch != null
      ) {
        this.addRegexMatchCondition();
      }
      if (
        condition.conditionType === RegistryFinderConditionType.SIZE &&
        condition.size != null
      ) {
        this.addSizeCondition();
      }
    }

    super.resetFlowArgs(flowArgs);
  }

  override convertFlowArgsToFormState(
    flowArgs: RegistryFinderArgs,
  ): ControlValues<Controls> {
    const regexMatchConditions = flowArgs.conditions
      ?.filter(
        (condition) =>
          condition.conditionType ===
            RegistryFinderConditionType.VALUE_REGEX_MATCH &&
          condition.valueRegexMatch != null,
      )
      .map((condition) => condition.valueRegexMatch!);

    const literalMatchConditions = flowArgs.conditions
      ?.filter(
        (condition) =>
          condition.conditionType ===
            RegistryFinderConditionType.VALUE_LITERAL_MATCH &&
          condition.valueLiteralMatch != null,
      )
      .map((condition) => condition.valueLiteralMatch!);
    const modificationTimeConditions = flowArgs.conditions
      ?.filter(
        (condition) =>
          condition.conditionType ===
            RegistryFinderConditionType.MODIFICATION_TIME &&
          condition.modificationTime != null,
      )
      .map((condition) => condition.modificationTime!);
    const sizeConditions = flowArgs.conditions
      ?.filter(
        (condition) =>
          condition.conditionType === RegistryFinderConditionType.SIZE &&
          condition.size != null,
      )
      .map((condition) => condition.size!);

    return {
      keysPaths: flowArgs.keysPaths?.length ? [...flowArgs.keysPaths] : [''],
      valueRegexMatches:
        regexMatchConditions?.map((condition) => {
          return {
            regex: condition.regex ? decodeBase64ToString(condition.regex) : '',
            mode: condition.mode,
            length: condition.length ? Number(condition.length) : undefined,
          };
        }) ?? [],
      valueLiteralMatches:
        literalMatchConditions?.map((condition) => {
          return {
            literal: condition.literal
              ? decodeBase64ToString(condition.literal)
              : '',
            mode: condition.mode,
          };
        }) ?? [],
      modificationTimes:
        modificationTimeConditions?.map((condition) => {
          return {
            fromTime: createOptionalDate(condition.minLastModifiedTime),
            toTime: createOptionalDate(condition.maxLastModifiedTime),
          };
        }) ?? [],
      sizes:
        sizeConditions?.map((condition) => {
          return {
            minFileSize: condition.minFileSize
              ? Number(condition.minFileSize)
              : undefined,
            maxFileSize: condition.maxFileSize
              ? Number(condition.maxFileSize)
              : undefined,
          };
        }) ?? [],
    };
  }

  addKeysPathExpression() {
    this.controls.keysPaths.push(new FormControlWithWarnings());
  }

  removeKeysPathExpression(index: number) {
    this.controls.keysPaths.removeAt(index);
  }

  addLiteralMatchCondition() {
    this.controls.valueLiteralMatches.push(createLiteralMatchFormGroup());
  }

  removeLiteralMatchCondition(index: number) {
    this.controls.valueLiteralMatches.removeAt(index);
  }

  addRegexMatchCondition() {
    this.controls.valueRegexMatches.push(createRegexMatchFormGroup());
  }

  removeRegexMatchCondition(index: number) {
    this.controls.valueRegexMatches.removeAt(index);
  }

  addModificationTimeCondition() {
    this.controls.modificationTimes.push(createTimeRangeFormGroup());
  }

  removeModificationTimeCondition(index: number) {
    this.controls.modificationTimes.removeAt(index);
  }

  addSizeCondition() {
    this.controls.sizes.push(createFileSizeRangeFormGroup());
  }

  removeSizeCondition(index: number) {
    this.controls.sizes.removeAt(index);
  }
}
