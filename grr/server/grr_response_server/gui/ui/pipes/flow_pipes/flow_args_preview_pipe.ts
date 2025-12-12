import {Pipe, PipeTransform} from '@angular/core';

import {
  ArtifactCollectorFlowArgs,
  CollectBrowserHistoryArgs,
  CollectFilesByKnownPathArgs,
  CollectLargeFileFlowArgs,
  CollectMultipleFilesArgs,
  ExecutePythonHackArgs,
  FileFinderArgs,
  HashMultipleFilesArgs,
  LaunchBinaryArgs,
  ListDirectoryArgs,
  ListProcessesArgs,
  MultiGetFileArgs,
  NetstatArgs,
  OsqueryFlowArgs,
  ReadLowLevelArgs,
  RecursiveListDirectoryArgs,
  RegistryFinderArgs,
  StatMultipleFilesArgs,
  TimelineArgs,
  UpdateClientArgs,
  YaraProcessDumpArgs,
} from '../../lib/api/api_interfaces';
import {FlowType} from '../../lib/models/flow';
import {checkExhaustive} from '../../lib/utils';

/**
 * Pipe that returns a friendly name for a flow.
 */
@Pipe({name: 'flowArgsPreview', standalone: true, pure: true})
export class FlowArgsPreviewPipe implements PipeTransform {
  transform(flowArgs: {} | undefined, flowType: FlowType | undefined): string {
    if (flowArgs === undefined || flowType === undefined) {
      return '';
    }
    switch (flowType) {
      case FlowType.ARTIFACT_COLLECTOR_FLOW:
        const artifactCollectorFlowArgs = flowArgs as ArtifactCollectorFlowArgs;
        return artifactCollectorFlowArgs.artifactList?.join(', ') || '';
      case FlowType.COLLECT_BROWSER_HISTORY:
        const collectBrowserHistoryArgs = flowArgs as CollectBrowserHistoryArgs;
        return collectBrowserHistoryArgs.browsers?.join(', ') || '';
      case FlowType.COLLECT_FILES_BY_KNOWN_PATH:
        const collectFilesByKnownPathArgs =
          flowArgs as CollectFilesByKnownPathArgs;
        return collectFilesByKnownPathArgs.paths?.join(', ') || '';
      case FlowType.COLLECT_LARGE_FILE_FLOW:
        const collectLargeFileFlowArgs = flowArgs as CollectLargeFileFlowArgs;
        return collectLargeFileFlowArgs.pathSpec?.path || '';
      case FlowType.COLLECT_MULTIPLE_FILES:
        const collectMultipleFilesArgs = flowArgs as CollectMultipleFilesArgs;
        return collectMultipleFilesArgs.pathExpressions?.join(', ') || '';
      case FlowType.EXECUTE_PYTHON_HACK:
        const executePythonHackArgs = flowArgs as ExecutePythonHackArgs;
        return executePythonHackArgs.hackName || '';
      case FlowType.CLIENT_FILE_FINDER:
      case FlowType.FILE_FINDER:
        const fileFinderArgs = flowArgs as FileFinderArgs;
        return fileFinderArgs.paths?.join(', ') || '';
      case FlowType.HASH_MULTIPLE_FILES:
        const hashMultipleFilesArgs = flowArgs as HashMultipleFilesArgs;
        return hashMultipleFilesArgs.pathExpressions?.join(', ') || '';
      case FlowType.LAUNCH_BINARY:
        const launchBinaryArgs = flowArgs as LaunchBinaryArgs;
        return launchBinaryArgs.binary?.toString() || '';
      case FlowType.LIST_DIRECTORY:
        const listDirectoryArgs = flowArgs as ListDirectoryArgs;
        return listDirectoryArgs.pathspec?.path || '';
      case FlowType.LIST_PROCESSES:
        const listProcessesArgs = flowArgs as ListProcessesArgs;
        const summary = [];
        if (listProcessesArgs.filenameRegex) {
          summary.push(listProcessesArgs.filenameRegex);
        }
        if (listProcessesArgs.fetchBinaries) {
          summary.push('with binaries');
        }
        if (listProcessesArgs.connectionStates) {
          summary.push(
            listProcessesArgs.connectionStates
              .map((state) => state.toString())
              .join(', '),
          );
        }
        if (listProcessesArgs.pids) {
          summary.push(listProcessesArgs.pids.join(', '));
        }
        return summary.join(' - ') || '';
      case FlowType.MULTI_GET_FILE:
        const multiGetFileArgs = flowArgs as MultiGetFileArgs;
        return (
          multiGetFileArgs.pathspecs
            ?.map((pathspec) => pathspec.path)
            .join(', ') || ''
        );
      case FlowType.NETSTAT:
        const netstatArgs = flowArgs as NetstatArgs;
        return netstatArgs.listeningOnly ? 'listening only' : 'all';
      case FlowType.OS_QUERY_FLOW:
        const osqueryFlowArgs = flowArgs as OsqueryFlowArgs;
        return osqueryFlowArgs.query || '';
      case FlowType.READ_LOW_LEVEL:
        const readLowLevelArgs = flowArgs as ReadLowLevelArgs;
        return readLowLevelArgs.path || '';
      case FlowType.RECURSIVE_LIST_DIRECTORY:
        const recursiveListDirectoryArgs =
          flowArgs as RecursiveListDirectoryArgs;
        return recursiveListDirectoryArgs.pathspec?.path || '';
      case FlowType.REGISTRY_FINDER:
      case FlowType.CLIENT_REGISTRY_FINDER:
        const registryFinderArgs = flowArgs as RegistryFinderArgs;
        return registryFinderArgs.keysPaths?.join(', ') || '';
      case FlowType.STAT_MULTIPLE_FILES:
        const statMultipleFilesArgs = flowArgs as StatMultipleFilesArgs;
        return statMultipleFilesArgs.pathExpressions?.join(', ') || '';
      case FlowType.TIMELINE_FLOW:
        const timelineFlowArgs = flowArgs as TimelineArgs;
        return timelineFlowArgs.root?.toString() || '';
      case FlowType.UPDATE_CLIENT:
        const updateClientArgs = flowArgs as UpdateClientArgs;
        return updateClientArgs.binaryPath || '';
      case FlowType.YARA_PROCESS_SCAN:
        const yaraProcessScanArgs = flowArgs as YaraProcessDumpArgs;
        const yaraProcessScanSummary = [];
        if (yaraProcessScanArgs.pids) {
          yaraProcessScanSummary.push(yaraProcessScanArgs.pids.join(', '));
        }
        if (yaraProcessScanArgs.processRegex) {
          yaraProcessScanSummary.push(yaraProcessScanArgs.processRegex);
        }
        return yaraProcessScanSummary.join(' - ') || '';
      case FlowType.COLLECT_CLOUD_VM_METADATA:
      case FlowType.COLLECT_DISTRO_INFO:
      case FlowType.COLLECT_HARDWARE_INFO:
      case FlowType.COLLECT_INSTALLED_SOFTWARE:
      case FlowType.DELETE_GRR_TEMP_FILES:
      case FlowType.DUMP_PROCESS_MEMORY:
      case FlowType.GET_CROWDSTRIKE_AGENT_ID:
      case FlowType.GET_MBR:
      case FlowType.GET_MEMORY_SIZE:
      case FlowType.INTERROGATE:
      case FlowType.KILL:
      case FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW:
      case FlowType.LIST_CONTAINERS:
      case FlowType.LIST_NAMED_PIPES_FLOW:
      case FlowType.LIST_RUNNING_SERVICES:
      case FlowType.LIST_VOLUME_SHADOW_COPIES:
      case FlowType.ONLINE_NOTIFICATION:
        return '';
      default:
        checkExhaustive(flowType, 'flowType had an unknown type');
    }
  }
}
