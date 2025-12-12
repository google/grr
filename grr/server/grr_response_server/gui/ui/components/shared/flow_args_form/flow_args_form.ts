import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {Client} from '../../../lib/models/client';
import {FlowType} from '../../../lib/models/flow';
import {ArtifactCollectorFlowForm} from './artifact_collector_flow_form';
import {ClientRegistryFinderForm} from './client_registry_finder_form';
import {CollectBrowserHistoryForm} from './collect_browser_history_form';
import {CollectFilesByKnownPathForm} from './collect_files_by_known_path_form';
import {CollectLargeFileFlowForm} from './collect_large_file_flow_form';
import {CollectMultipleFilesForm} from './collect_multiple_files_form';
import {DumpProcessMemoryForm} from './dump_process_memory_form';
import {ExecutePythonHackForm} from './execute_python_hack_form';
import {GetMBRForm} from './get_mbr_form';
import {HashMultipleFilesForm} from './hash_multiple_files_form';
import {InterrogateForm} from './interrogate_form';
import {KillGrrForm} from './kill_grr_form';
import {LaunchBinaryForm} from './launch_binary_form';
import {ListDirectoryForm} from './list_directory_form';
import {ListNamedPipesForm} from './list_named_pipes_form';
import {ListProcessesForm} from './list_processes_form';
import {NetstatForm} from './netstat_form';
import {OnlineNotificationForm} from './online_notification_form';
import {OsqueryForm} from './osquery_form';
import {ReadLowLevelForm} from './read_low_level_form';
import {StatMultipleFilesForm} from './stat_multiple_files_form';
import {TimelineForm} from './timeline_form';
import {YaraProcessScanForm} from './yara_process_scan_form';

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'flow-args-form',
  templateUrl: './flow_args_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    ArtifactCollectorFlowForm,
    CollectBrowserHistoryForm,
    CollectFilesByKnownPathForm,
    CollectLargeFileFlowForm,
    CollectMultipleFilesForm,
    DumpProcessMemoryForm,
    ExecutePythonHackForm,
    GetMBRForm,
    HashMultipleFilesForm,
    InterrogateForm,
    KillGrrForm,
    LaunchBinaryForm,
    ListDirectoryForm,
    ListNamedPipesForm,
    ListProcessesForm,
    NetstatForm,
    OnlineNotificationForm,
    OsqueryForm,
    ReadLowLevelForm,
    ClientRegistryFinderForm,
    StatMultipleFilesForm,
    TimelineForm,
    YaraProcessScanForm,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowArgsForm {
  /** The name of the flow the form belongs to. */
  readonly flowType = input.required<FlowType>();

  // The flow args to be displayed in the form. If not set, the form will be
  // populated with the default flow args.
  readonly flowArgs = input<object>();

  /** Whether the form is editable. */
  readonly editable = input<boolean>(true);

  /* The onSubmit function to be called when the form is submitted. */
  readonly onSubmit = input<(flowName: string, flowArgs: object) => void>(
    (flowName, flowArgs) => {},
  );

  /**
   * The client the form is being used for.
   * Some flow form filter options based on client os, give examples for
   * knowledge base values for a specific client etc.
   * This is optional, if not provided the form will not display client specific
   * information.
   */
  readonly client = input<Client>();

  protected readonly FlowType = FlowType;
}
