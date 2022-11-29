import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {YaraProcessDumpArgs} from '../../lib/api/api_interfaces';


enum FilterMode {
  NAME,
  PID,
  ALL
}

function makeControls() {
  return {
    filterMode: new FormControl(FilterMode.PID, {nonNullable: true}),
    dumpAllProcesses: new FormControl(false, {nonNullable: true}),
    processRegex: new FormControl('', {nonNullable: true}),
    pids: new FormControl<number[]>([], {nonNullable: true}),
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
  selector: 'app-dump-process-memory-form',
  templateUrl: './dump_process_memory_form.ng.html',
  styleUrls: ['./dump_process_memory_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class DumpProcessMemoryForm extends
    FlowArgumentForm<YaraProcessDumpArgs, Controls> {
  readonly filterMode = FilterMode;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: YaraProcessDumpArgs) {
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
      dumpAllProcesses: flowArgs.dumpAllProcesses ??
          this.controls.dumpAllProcesses.defaultValue,
      processRegex:
          flowArgs.processRegex ?? this.controls.processRegex.defaultValue,
      skipSpecialRegions: flowArgs.skipSpecialRegions ??
          this.controls.skipSpecialRegions.defaultValue,
      skipMappedFiles: flowArgs.skipMappedFiles ??
          this.controls.skipMappedFiles.defaultValue,
      skipSharedRegions: flowArgs.skipSharedRegions ??
          this.controls.skipSharedRegions.defaultValue,
      skipExecutableRegions: flowArgs.skipExecutableRegions ??
          this.controls.skipExecutableRegions.defaultValue,
      skipReadonlyRegions: flowArgs.skipReadonlyRegions ??
          this.controls.skipReadonlyRegions.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      pids: formState.filterMode === FilterMode.PID ?
          formState.pids.map(pid => pid.toString()) :
          undefined,
      processRegex: formState.filterMode === FilterMode.NAME ?
          formState.processRegex :
          undefined,
      dumpAllProcesses: formState.filterMode === FilterMode.ALL,
      skipSpecialRegions: formState.skipSpecialRegions,
      skipMappedFiles: formState.skipMappedFiles,
      skipSharedRegions: formState.skipSharedRegions,
      skipExecutableRegions: formState.skipExecutableRegions,
      skipReadonlyRegions: formState.skipReadonlyRegions,
    };
  }
}
