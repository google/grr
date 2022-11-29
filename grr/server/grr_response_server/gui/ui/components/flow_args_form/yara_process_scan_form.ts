import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {YaraProcessScanRequest} from '../../lib/api/api_interfaces';
import {CodeEditor} from '../code_editor/code_editor';


enum FilterMode {
  NAME,
  PID,
  CMDLINE,
  ALL
}

function makeControls() {
  return {
    yaraSignature: new FormControl(DEFAULT_RULE, {nonNullable: true}),
    filterMode: new FormControl(FilterMode.ALL, {nonNullable: true}),
    processRegex: new FormControl('', {nonNullable: true}),
    cmdlineRegex: new FormControl('', {nonNullable: true}),
    pids: new FormControl<ReadonlyArray<number>>([], {nonNullable: true}),
    skipSpecialRegions: new FormControl(false, {nonNullable: true}),
    skipMappedFiles: new FormControl(false, {nonNullable: true}),
    skipSharedRegions: new FormControl(false, {nonNullable: true}),
    skipExecutableRegions: new FormControl(false, {nonNullable: true}),
    skipReadonlyRegions: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

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

/** Form that configures a DumpProcessMemory flow. */
@Component({
  selector: 'app-yara-process-scan-form',
  templateUrl: './yara_process_scan_form.ng.html',
  styleUrls: ['./yara_process_scan_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class YaraProcessScanForm extends
    FlowArgumentForm<YaraProcessScanRequest, Controls> {
  readonly filterMode = FilterMode;

  @ViewChild(CodeEditor) codeEditor?: CodeEditor;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: YaraProcessScanRequest) {
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
      processRegex:
          flowArgs.processRegex ?? this.controls.processRegex.defaultValue,
      cmdlineRegex:
          flowArgs.cmdlineRegex ?? this.controls.cmdlineRegex.defaultValue,
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
      yaraSignature: formState.yaraSignature,
      pids: formState.filterMode === FilterMode.PID ?
          formState.pids?.map(pid => pid.toString()) :
          undefined,
      processRegex: formState.filterMode === FilterMode.NAME ?
          formState.processRegex :
          undefined,
      cmdlineRegex: formState.filterMode === FilterMode.CMDLINE ?
          formState.cmdlineRegex :
          undefined,

      skipSpecialRegions: formState.skipSpecialRegions,
      skipMappedFiles: formState.skipMappedFiles,
      skipSharedRegions: formState.skipSharedRegions,
      skipExecutableRegions: formState.skipExecutableRegions,
      skipReadonlyRegions: formState.skipReadonlyRegions,
    };
  }

  override focus(container: HTMLElement): void {
    this.codeEditor?.focus();
  }
}
