/** PayloadType maps types of result payloads. */
export enum PayloadType {
  API_HUNT_ERROR = 'ApiHuntError',
  API_HUNT_RESULT = 'ApiHuntResult',
  BYTES_VALUE = 'BytesValue',
  CLIENT_SNAPSHOT = 'ClientSnapshot',
  COLLECT_BROWSER_HISTORY_RESULT = 'CollectBrowserHistoryResult',
  COLLECT_DISTRO_INFO_RESULT = 'CollectDistroInfoResult',
  COLLECT_FILES_BY_KNOWN_PATH_RESULT = 'CollectFilesByKnownPathResult',
  COLLECT_LARGE_FILE_FLOW_RESULT = 'CollectLargeFileFlowResult',
  COLLECT_MULTIPLE_FILES_RESULT = 'CollectMultipleFilesResult',
  COLLECT_CLOUD_VM_METADATA_RESULT = 'CollectCloudVMMetadataResult',
  DICT = 'Dict',
  EXECUTE_BINARY_RESPONSE = 'ExecuteBinaryResponse',
  EXECUTE_PYTHON_HACK_RESULT = 'ExecutePythonHackResult',
  EXECUTE_RESPONSE = 'ExecuteResponse',
  FILE_FINDER_RESULT = 'FileFinderResult',
  GET_CROWDSTRIKE_AGENT_ID_RESULT = 'GetCrowdstrikeAgentIdResult',
  GET_MEMORY_SIZE_RESULT = 'GetMemorySizeResult',
  HARDWARE_INFO = 'HardwareInfo',
  KNOWLEDGE_BASE = 'KnowledgeBase',
  LIST_CONTAINERS_FLOW_RESULT = 'ListContainersFlowResult',
  LIST_NAMED_PIPES_FLOW_RESULT = 'ListNamedPipesFlowResult',
  NETWORK_CONNECTION = 'NetworkConnection',
  OSQUERY_RESULT = 'OsqueryResult',
  OSX_SERVICE_INFORMATION = 'OsxServiceInformation',
  PROCESS = 'Process',
  PROCESS_MEMORY_ERROR = 'ProcessMemoryError',
  READ_LOW_LEVEL_FLOW_RESULT = 'ReadLowLevelFlowResult',
  SOFTWARE_PACKAGES = 'SoftwarePackages',
  STAT_ENTRY = 'StatEntry',
  STENOGRAPHER_UPLOAD_FLOW_RESULT = 'StenographerUploadFlowResult',
  TIMELINE_RESULT = 'TimelineResult',
  USER = 'User',
  YARA_PROCESS_DUMP_RESPONSE = 'YaraProcessDumpResponse',
  YARA_PROCESS_SCAN_MATCH = 'YaraProcessScanMatch',
  YARA_PROCESS_SCAN_MISS = 'YaraProcessScanMiss',
}

/**
 * typeUrlToPayloadType returns the PayloadType for a given typeUrl.
 */
export function typeUrlToPayloadType(
  typeUrl: string | undefined,
): PayloadType | undefined {
  const typeName = typeUrl?.split('.').pop();
  switch (typeName) {
    case 'ApiHuntError':
      return PayloadType.API_HUNT_ERROR;
    case 'ApiHuntResult':
      return PayloadType.API_HUNT_RESULT;
    case 'ClientSnapshot':
      return PayloadType.CLIENT_SNAPSHOT;
    case 'CollectBrowserHistoryResult':
      return PayloadType.COLLECT_BROWSER_HISTORY_RESULT;
    case 'CollectFilesByKnownPathResult':
      return PayloadType.COLLECT_FILES_BY_KNOWN_PATH_RESULT;
    case 'CollectLargeFileFlowResult':
      return PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT;
    case 'CollectMultipleFilesResult':
      return PayloadType.COLLECT_MULTIPLE_FILES_RESULT;
    case 'CollectDistroInfoResult':
      return PayloadType.COLLECT_DISTRO_INFO_RESULT;
    case 'CollectCloudVMMetadataResult':
      return PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT;
    case 'ExecuteBinaryResponse':
      return PayloadType.EXECUTE_BINARY_RESPONSE;
    case 'ExecutePythonHackResult':
      return PayloadType.EXECUTE_PYTHON_HACK_RESULT;
    case 'ExecuteResponse':
      return PayloadType.EXECUTE_RESPONSE;
    case 'FileFinderResult':
      return PayloadType.FILE_FINDER_RESULT;
    case 'GetCrowdstrikeAgentIdResult':
      return PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT;
    case 'GetMemorySizeResult':
      return PayloadType.GET_MEMORY_SIZE_RESULT;
    case 'HardwareInfo':
      return PayloadType.HARDWARE_INFO;
    case 'KnowledgeBase':
      return PayloadType.KNOWLEDGE_BASE;
    case 'ListContainersFlowResult':
      return PayloadType.LIST_CONTAINERS_FLOW_RESULT;
    case 'ListNamedPipesFlowResult':
      return PayloadType.LIST_NAMED_PIPES_FLOW_RESULT;
    case 'NetworkConnection':
      return PayloadType.NETWORK_CONNECTION;
    case 'OsqueryResult':
      return PayloadType.OSQUERY_RESULT;
    case 'OsxServiceInformation':
      return PayloadType.OSX_SERVICE_INFORMATION;
    case 'Process':
      return PayloadType.PROCESS;
    case 'ProcessMemoryError':
      return PayloadType.PROCESS_MEMORY_ERROR;
    case 'ReadLowLevelFlowResult':
      return PayloadType.READ_LOW_LEVEL_FLOW_RESULT;
    case 'SoftwarePackages':
      return PayloadType.SOFTWARE_PACKAGES;
    case 'StatEntry':
      return PayloadType.STAT_ENTRY;
    case 'StenographerUploadFlowResult':
      return PayloadType.STENOGRAPHER_UPLOAD_FLOW_RESULT;
    case 'TimelineResult':
      return PayloadType.TIMELINE_RESULT;
    case 'User':
      return PayloadType.USER;
    case 'YaraProcessDumpResponse':
      return PayloadType.YARA_PROCESS_DUMP_RESPONSE;
    case 'YaraProcessScanMatch':
      return PayloadType.YARA_PROCESS_SCAN_MATCH;
    case 'YaraProcessScanMiss':
      return PayloadType.YARA_PROCESS_SCAN_MISS;
    default:
      return undefined;
  }
}

/**
 * CollectionResult represents a single collection result.
 */
export interface CollectionResult {
  readonly clientId: string;
  readonly payloadType: PayloadType | undefined;
  readonly payload: unknown;
  readonly timestamp: Date;
}
