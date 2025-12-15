import {ComponentHarness} from '@angular/cdk/testing';

import {ArtifactCollectorFlowFormHarness} from './artifact_collector_flow_form_harness';
import {ClientRegistryFinderFormHarness} from './client_registry_finder_form_harness';
import {CollectBrowserHistoryFormHarness} from './collect_browser_history_form_harness';
import {CollectFilesByKnownPathFormHarness} from './collect_files_by_known_path_form_harness';
import {CollectLargeFileFlowFormHarness} from './collect_large_file_flow_form_harness';
import {CollectMultipleFilesFormHarness} from './collect_multiple_files_form_harness';
import {DumpProcessMemoryFormHarness} from './dump_process_memory_form_harness';
import {ExecutePythonHackFormHarness} from './execute_python_hack_form_harness';
import {GetMBRFormHarness} from './get_mbr_form_harness';
import {HashMultipleFilesFormHarness} from './hash_multiple_files_form_harness';
import {InterrogateFormHarness} from './interrogate_form_harness';
import {KillGrrFormHarness} from './kill_grr_form_harness';
import {LaunchBinaryFormHarness} from './launch_binary_form_harness';
import {ListDirectoryFormHarness} from './list_directory_form_harness';
import {ListNamedPipesFormHarness} from './list_named_pipes_form_harness';
import {ListProcessesFormHarness} from './list_processes_form_harness';
import {NetstatFormHarness} from './netstat_form_harness';
import {OnlineNotificationFormHarness} from './online_notification_form_harness';
import {OsqueryFormHarness} from './osquery_form_harness';
import {ReadLowLevelFormHarness} from './read_low_level_form_harness';
import {StatMultipleFilesFormHarness} from './stat_multiple_files_form_harness';
import {TimelineFormHarness} from './timeline_form_harness';
import {YaraProcessScanFormHarness} from './yara_process_scan_form_harness';

/** Harness for the ApprovalChip component. */
export class FlowArgsFormHarness extends ComponentHarness {
  static hostSelector = 'flow-args-form';

  private readonly fieldset = this.locatorFor('fieldset');

  async isDisabled(): Promise<boolean> {
    return (await this.fieldset()).getProperty('disabled') ?? false;
  }

  /**
   * Harness for the ArtifactCollectorFlowForm component.
   */
  readonly artifactCollectorFlowForm = this.locatorFor(
    ArtifactCollectorFlowFormHarness,
  );

  /**
   * Harness for the ClientRegistryFinderForm component.
   */
  readonly clientRegistryFinderForm = this.locatorFor(
    ClientRegistryFinderFormHarness,
  );

  /**
   * Harness for the CollectBrowserHistoryForm component.
   */
  readonly collectBrowserHistoryForm = this.locatorFor(
    CollectBrowserHistoryFormHarness,
  );

  /**
   * Harness for the CollectFilesByKnownPathForm component.
   */
  readonly collectFilesByKnownPathForm = this.locatorFor(
    CollectFilesByKnownPathFormHarness,
  );

  /**
   * Harness for the CollectLargeFileFlowForm component.
   */
  readonly collectLargeFileFlowForm = this.locatorFor(
    CollectLargeFileFlowFormHarness,
  );

  /**
   * Harness for the CollectMultipleFilesForm component.
   */
  readonly collectMultipleFilesForm = this.locatorFor(
    CollectMultipleFilesFormHarness,
  );

  /**
   * Harness for the DumpProcessMemoryForm component.
   */
  readonly dumpProcessMemoryForm = this.locatorFor(
    DumpProcessMemoryFormHarness,
  );

  /**
   * Harness for the ExecutePythonHackForm component.
   */
  readonly executePythonHackForm = this.locatorFor(
    ExecutePythonHackFormHarness,
  );

  /**
   * Harness for the GetMBRForm component.
   */
  readonly getMBRForm = this.locatorFor(GetMBRFormHarness);

  /**
   * Harness for the HashMultipleFilesForm component.
   */
  readonly hashMultipleFilesForm = this.locatorFor(
    HashMultipleFilesFormHarness,
  );

  /**
   * Harness for the InterrogateForm component.
   */
  readonly interrogateForm = this.locatorFor(InterrogateFormHarness);

  /**
   * Harness for the KillGrrForm component.
   */
  readonly killGrrForm = this.locatorFor(KillGrrFormHarness);

  /**
   * Harness for the LaunchBinaryForm component.
   */
  readonly launchBinaryForm = this.locatorFor(LaunchBinaryFormHarness);

  /**
   * Harness for the ListDirectoryForm component.
   */
  readonly listDirectoryForm = this.locatorFor(ListDirectoryFormHarness);

  /**
   * Harness for the ListNamedPipesForm component.
   */
  readonly listNamedPipesForm = this.locatorFor(ListNamedPipesFormHarness);

  /**
   * Harness for the ListProcessesForm component.
   */
  readonly listProcessesForm = this.locatorFor(ListProcessesFormHarness);

  /**
   * Harness for the NetstatForm component.
   */
  readonly netstatForm = this.locatorFor(NetstatFormHarness);

  /**
   * Harness for the OnlineNotificationForm component.
   */
  readonly onlineNotificationForm = this.locatorFor(
    OnlineNotificationFormHarness,
  );

  /**
   * Harness for the OsqueryForm component.
   */
  readonly osqueryForm = this.locatorFor(OsqueryFormHarness);

  /**
   * Harness for the ReadLowLevelForm component.
   */
  readonly readLowLevelForm = this.locatorFor(ReadLowLevelFormHarness);

  /**
   * Harness for the StatMultipleFilesForm component.
   */
  readonly statMultipleFilesForm = this.locatorFor(
    StatMultipleFilesFormHarness,
  );

  /**
   * Harness for the ReadLowLevelForm component.
   */
  readonly timelineForm = this.locatorFor(TimelineFormHarness);

  /**
   * Harness for the YaraProcessScanForm component.
   */
  readonly yaraProcessScanForm = this.locatorFor(YaraProcessScanFormHarness);
}
