import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {YaraProcessDumpArgs} from '../../../lib/api/api_interfaces';
import {CommaSeparatedNumberValueAccessor} from '../form/comma_separated_input/comma_separated_value_accessor';
import {FormErrors, integerArrayValidator} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

/** Filter mode for the DumpProcessMemory form. */
export enum FilterMode {
  NAME,
  PID,
  ALL,
}

function makeControls() {
  return {
    filterMode: new FormControl(FilterMode.PID, {nonNullable: true}),
    dumpAllProcesses: new FormControl(false, {nonNullable: true}),
    processRegex: new FormControl('', {
      nonNullable: true,
    }),
    pids: new FormControl<number[]>([], {
      nonNullable: true,
      validators: [integerArrayValidator()],
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
  selector: 'dump-process-memory-form',
  templateUrl: './dump_process_memory_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    CommaSeparatedNumberValueAccessor,
    FormErrors,
    FormsModule,
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
export class DumpProcessMemoryForm extends FlowArgsFormInterface<
  YaraProcessDumpArgs,
  Controls
> {
  readonly filterMode = FilterMode;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: YaraProcessDumpArgs,
  ): ControlValues<Controls> {
    let filterMode = this.controls.filterMode.defaultValue;

    if (flowArgs.dumpAllProcesses) {
      filterMode = FilterMode.ALL;
    } else if (flowArgs.pids?.length) {
      filterMode = FilterMode.PID;
    } else if (flowArgs.processRegex) {
      filterMode = FilterMode.NAME;
    }

    return {
      filterMode,
      pids: flowArgs.pids?.map(Number) ?? this.controls.pids.defaultValue,
      dumpAllProcesses:
        flowArgs.dumpAllProcesses ??
        this.controls.dumpAllProcesses.defaultValue,
      processRegex:
        flowArgs.processRegex ?? this.controls.processRegex.defaultValue,
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
  ): YaraProcessDumpArgs {
    return {
      pids:
        formState.filterMode === FilterMode.PID
          ? formState.pids.map((pid) => pid.toString())
          : undefined,
      processRegex:
        formState.filterMode === FilterMode.NAME
          ? formState.processRegex ?? undefined
          : undefined,
      dumpAllProcesses: formState.filterMode === FilterMode.ALL,
      skipSpecialRegions: formState.skipSpecialRegions,
      skipMappedFiles: formState.skipMappedFiles,
      skipSharedRegions: formState.skipSharedRegions,
      skipExecutableRegions: formState.skipExecutableRegions,
      skipReadonlyRegions: formState.skipReadonlyRegions,
    };
  }
}
