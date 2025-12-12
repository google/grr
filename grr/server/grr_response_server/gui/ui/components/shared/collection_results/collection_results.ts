import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {ClientSnapshots} from './client_snapshots';
import {CollectBrowserHistoryResults} from './collect_browser_history_results';
import {CollectCloudVmMetadataResults} from './collect_cloud_vm_metadata_results';
import {CollectDistroInfoResults} from './collect_distro_info_results';
import {CollectFilesByKnownPathResults} from './collect_files_by_known_path_results';
import {CollectLargeFileFlowResults} from './collect_large_file_flow_results';
import {CollectMultipleFilesResults} from './collect_multiple_files_results';
import {ExecuteBinaryResponses} from './execute_binary_responses';
import {ExecutePythonHackResults} from './execute_python_hack_results';
import {ExecuteResponseResults} from './execute_response_results';
import {FileFinderResults} from './file_finder_results';
import {GetCrowdstrikeAgentIdResults} from './get_crowdstrike_agent_id_results';
import {GetMemorySizeResults} from './get_memory_size_results';
import {HardwareInfos} from './hardware_infos';
import {KnowledgeBases} from './knowledge_bases';
import {ListContainersFlowResults} from './list_containers_flow_results';
import {NetworkConnections} from './network_connections';
import {OsqueryResults} from './osquery_results';
import {Processes} from './processes';
import {ReadLowLevelFlowResults} from './read_low_level_flow_results';
import {SoftwarePackagez} from './software_packagez';
import {StatEntryResults} from './stat_entry_results';
import {Users} from './users';
import {YaraProcessDumpResponses} from './yara_process_dump_responses';
import {YaraProcessScanMatches} from './yara_process_scan_matches';

/** Details and results of LaunchBinary flow. */
@Component({
  selector: 'collection-results',
  templateUrl: './collection_results.ng.html',
  imports: [
    ClientSnapshots,
    CollectBrowserHistoryResults,
    CollectCloudVmMetadataResults,
    CollectDistroInfoResults,
    CollectFilesByKnownPathResults,
    CollectLargeFileFlowResults,
    CollectMultipleFilesResults,
    CommonModule,
    ExecutePythonHackResults,
    ExecuteBinaryResponses,
    ExecuteResponseResults,
    FileFinderResults,
    GetCrowdstrikeAgentIdResults,
    GetMemorySizeResults,
    HardwareInfos,
    KnowledgeBases,
    ListContainersFlowResults,
    NetworkConnections,
    OsqueryResults,
    Processes,
    ReadLowLevelFlowResults,
    SoftwarePackagez,
    StatEntryResults,
    Users,
    YaraProcessScanMatches,
    YaraProcessDumpResponses,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectionResults {
  /** Loaded results to display in the table. */
  readonly collectionResultsByType = input.required<
    Map<PayloadType, readonly CollectionResult[]> | undefined
  >();

  // tslint:disable-next-line:enforce-name-casing
  protected PayloadType = PayloadType;
}
