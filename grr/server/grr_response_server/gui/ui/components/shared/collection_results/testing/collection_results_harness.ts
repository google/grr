import {ComponentHarness} from '@angular/cdk/testing';

import {ClientSnapshotsHarness} from './client_snapshots_harness';
import {CollectBrowserHistoryResultsHarness} from './collect_browser_history_results_harness';
import {CollectCloudVmMetadataResultsHarness} from './collect_cloud_vm_metadata_results_harness';
import {CollectDistroInfoResultsHarness} from './collect_distro_info_results_harness';
import {CollectFilesByKnownPathResultsHarness} from './collect_files_by_known_path_results_harness';
import {CollectLargeFileFlowResultsHarness} from './collect_large_file_flow_results_harness';
import {CollectMultipleFilesResultsHarness} from './collect_multiple_files_results_harness';
import {ExecuteBinaryResponsesHarness} from './execute_binary_responses_harness';
import {ExecutePythonHackResultsHarness} from './execute_python_hack_results_harness';
import {ExecuteResponseResultsHarness} from './execute_response_results_harness';
import {FileFinderResultsHarness} from './file_finder_results_harness';
import {GetCrowdstrikeAgentIdResultsHarness} from './get_crowdstrike_agent_id_results_harness';
import {GetMemorySizeResultsHarness} from './get_memory_size_results_harness';
import {HardwareInfosHarness} from './hardware_infos_harness';
import {KnowledgeBasesHarness} from './knowledge_bases_harness';
import {ListContainersFlowResultsHarness} from './list_containers_flow_results_harness';
import {NetworkConnectionsHarness} from './network_connections_harness';
import {OsqueryResultsHarness} from './osquery_results_harness';
import {ProcessesHarness} from './processes_harness';
import {ReadLowLevelFlowResultsHarness} from './read_low_level_flow_results_harness';
import {SoftwarePackagezHarness} from './software_packagez_harness';
import {StatEntryResultsHarness} from './stat_entry_results_harness';
import {UsersHarness} from './users_harness';
import {YaraProcessDumpResponsesHarness} from './yara_process_dump_responses_harness';
import {YaraProcessScanMatchesHarness} from './yara_process_scan_matches_harness';

/** Harness for the CollectionResults component. */
export class CollectionResultsHarness extends ComponentHarness {
  static hostSelector = 'collection-results';

  readonly clientSnapshots = this.locatorForOptional(ClientSnapshotsHarness);

  readonly collectBrowserHistoryResults = this.locatorForOptional(
    CollectBrowserHistoryResultsHarness,
  );

  readonly collectCloudVmMetadataResults = this.locatorForOptional(
    CollectCloudVmMetadataResultsHarness,
  );

  readonly collectDistroInfoResults = this.locatorForOptional(
    CollectDistroInfoResultsHarness,
  );

  readonly collectFilesByKnownPathResults = this.locatorForOptional(
    CollectFilesByKnownPathResultsHarness,
  );

  readonly collectLargeFileFlowResults = this.locatorForOptional(
    CollectLargeFileFlowResultsHarness,
  );

  readonly collectMultipleFilesResults = this.locatorForOptional(
    CollectMultipleFilesResultsHarness,
  );

  readonly executeBinaryResponses = this.locatorForOptional(
    ExecuteBinaryResponsesHarness,
  );

  readonly executePythonHackResults = this.locatorForOptional(
    ExecutePythonHackResultsHarness,
  );

  readonly executeResponseResults = this.locatorForOptional(
    ExecuteResponseResultsHarness,
  );

  readonly fileFinderResults = this.locatorForOptional(
    FileFinderResultsHarness,
  );

  readonly getCrowdstrikeAgentIdResults = this.locatorForOptional(
    GetCrowdstrikeAgentIdResultsHarness,
  );

  readonly getMemorySizeResults = this.locatorForOptional(
    GetMemorySizeResultsHarness,
  );

  readonly hardwareInfos = this.locatorForOptional(HardwareInfosHarness);

  readonly knowledgeBases = this.locatorForOptional(KnowledgeBasesHarness);

  readonly listContainersFlowResults = this.locatorForOptional(
    ListContainersFlowResultsHarness,
  );

  readonly networkConnections = this.locatorForOptional(
    NetworkConnectionsHarness,
  );

  readonly osqueryResults = this.locatorForOptional(OsqueryResultsHarness);

  readonly processes = this.locatorForOptional(ProcessesHarness);

  readonly readLowLevelFlowResults = this.locatorForOptional(
    ReadLowLevelFlowResultsHarness,
  );

  readonly softwarePackagez = this.locatorForOptional(SoftwarePackagezHarness);

  readonly statEntryResults = this.locatorForOptional(StatEntryResultsHarness);

  readonly users = this.locatorForOptional(UsersHarness);

  readonly yaraProcessScanMatches = this.locatorForOptional(
    YaraProcessScanMatchesHarness,
  );

  readonly yaraProcessDumpResponses = this.locatorForOptional(
    YaraProcessDumpResponsesHarness,
  );
}
