import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {windowOpen} from 'safevalues/dom';

import {YaraProcessScanRequest} from '../../../lib/api/api_interfaces';
import {ByteValueAccessor} from '../form/byte_input/byte_value_accessor';
import {CommaSeparatedNumberValueAccessor} from '../form/comma_separated_input/comma_separated_value_accessor';
import {
  FormErrors,
  integerArrayValidator,
  minValue,
} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

// Autoformatting changes literal tabs to spaces, which do not work as well in
// the CodeEditor. Use \t instead.
const DEFAULT_RULE = `rule Example
{
\tstrings:
\t\t$text_string = "hello world"
\t\t$hex_string = { 12 34 56 ?? 90 AB }

\tcondition:
\t\t$text_string or $hex_string
}`;

/** Filter mode for the YaraProcessScanForm. */
export enum FilterMode {
  NAME,
  PID,
  CMDLINE,
  ALL,
}

function makeControls() {
  return {
    yaraSignature: new FormControl(DEFAULT_RULE, {nonNullable: true}),
    filterMode: new FormControl(FilterMode.ALL, {nonNullable: true}),
    processRegex: new FormControl('', {nonNullable: true}),
    cmdlineRegex: new FormControl('', {nonNullable: true}),
    pids: new FormControl<readonly number[]>([], {
      nonNullable: true,
      validators: [integerArrayValidator()],
    }),
    contextWindow: new FormControl<number>(50, {
      nonNullable: true,
      validators: [minValue(0)],
    }),
    skipSpecialRegions: new FormControl(false, {nonNullable: true}),
    skipMappedFiles: new FormControl(false, {nonNullable: true}),
    skipSharedRegions: new FormControl(false, {nonNullable: true}),
    skipExecutableRegions: new FormControl(false, {nonNullable: true}),
    skipReadonlyRegions: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a DumpProcessMemory flow. */
@Component({
  selector: 'yara-process-scan-form',
  templateUrl: './yara_process_scan_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss', './yara_process_scan_form.scss'],
  imports: [
    CommaSeparatedNumberValueAccessor,
    ByteValueAccessor,
    CommonModule,
    FormErrors,
    MatButtonToggleModule,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class YaraProcessScanForm extends FlowArgsFormInterface<
  YaraProcessScanRequest,
  Controls
> {
  flowType = this.FlowType.YARA_PROCESS_SCAN;

  readonly filterMode = FilterMode;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: YaraProcessScanRequest,
  ): ControlValues<Controls> {
    let filterMode = this.controls.filterMode.defaultValue;

    if (flowArgs.pids?.length) {
      filterMode = FilterMode.PID;
    } else if (flowArgs.processRegex) {
      filterMode = FilterMode.NAME;
    } else if (flowArgs.cmdlineRegex) {
      filterMode = FilterMode.CMDLINE;
    }

    return {
      yaraSignature:
        flowArgs.yaraSignature ?? this.controls.yaraSignature.defaultValue,
      filterMode,
      pids: flowArgs.pids?.map(Number) ?? this.controls.pids.defaultValue,
      contextWindow:
        flowArgs.contextWindow ?? this.controls.contextWindow.defaultValue,
      processRegex:
        flowArgs.processRegex ?? this.controls.processRegex.defaultValue,
      cmdlineRegex:
        flowArgs.cmdlineRegex ?? this.controls.cmdlineRegex.defaultValue,
      skipSpecialRegions:
        flowArgs.skipSpecialRegions ??
        this.controls.skipSpecialRegions.defaultValue,
      skipMappedFiles:
        flowArgs.skipMappedFiles ?? this.controls.skipMappedFiles.defaultValue,
      skipSharedRegions:
        flowArgs.skipSharedRegions ??
        this.controls.skipSharedRegions.defaultValue,
      skipExecutableRegions:
        flowArgs.skipExecutableRegions ??
        this.controls.skipExecutableRegions.defaultValue,
      skipReadonlyRegions:
        flowArgs.skipReadonlyRegions ??
        this.controls.skipReadonlyRegions.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): YaraProcessScanRequest {
    return {
      yaraSignature: formState.yaraSignature,
      pids:
        formState.filterMode === FilterMode.PID
          ? formState.pids?.map((pid) => pid.toString())
          : undefined,
      processRegex:
        formState.filterMode === FilterMode.NAME
          ? formState.processRegex
          : undefined,
      cmdlineRegex:
        formState.filterMode === FilterMode.CMDLINE
          ? formState.cmdlineRegex
          : undefined,

      contextWindow: formState.contextWindow,
      skipSpecialRegions: formState.skipSpecialRegions,
      skipMappedFiles: formState.skipMappedFiles,
      skipSharedRegions: formState.skipSharedRegions,
      skipExecutableRegions: formState.skipExecutableRegions,
      skipReadonlyRegions: formState.skipReadonlyRegions,
    };
  }

  protected openLinkInNewTab(url: string) {
    windowOpen(window, url, '_blank');
  }
}
