import {FlowType} from '../../models/flow';

/**
 * Flow category.
 */
export enum FlowCategory {
  COLLECTORS = 'Collectors',
  BROWSER = 'Browser',
  HARDWARE = 'Hardware',
  FILESYSTEM = 'Filesystem',
  ADMINISTRATIVE = 'Administrative',
  PROCESSES = 'Processes',
  NETWORK = 'Network',
}

/**
 * FlowDetails encapsulates flow-related information.
 */
export interface FlowDetails {
  readonly type: FlowType;
  readonly friendlyName: string;
  readonly description: string;
  readonly category: FlowCategory;
  // Favorite flows are highlighted in the UI.
  readonly favorite?: boolean;
  readonly restricted: boolean;
  // Hidden flows cannot be launched from the UI, they might be launched from
  // other flows or from the CLI. We still want to show them in the UI to show
  // basic results, success information etc., but they should not be visible in
  // the "Start new flow" view.
  readonly hidden: boolean;
}

/**
 * Map of flow types to flow details.
 * Flow details are used to display flow information in the UI.
 * Keeping them in one place as this information is displayed in multiple
 * places in the UI.
 */
export const FLOW_DETAILS_BY_TYPE: ReadonlyMap<FlowType, FlowDetails> = new Map(
  [
    [
      FlowType.ARTIFACT_COLLECTOR_FLOW,
      {
        type: FlowType.ARTIFACT_COLLECTOR_FLOW,
        friendlyName: 'Collect a forensic artifact',
        description:
          'Collects a set of files/information defined by a forensic artifact from a client.',
        category: FlowCategory.COLLECTORS,
        favorite: true,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.CLIENT_FILE_FINDER,
      {
        type: FlowType.CLIENT_FILE_FINDER,
        friendlyName: 'Client file finder',
        description: 'Finds files on the client',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.CLIENT_REGISTRY_FINDER,
      {
        type: FlowType.CLIENT_REGISTRY_FINDER,
        friendlyName: 'Collect client registry keys',
        description: 'Collects client registry keys',
        category: FlowCategory.COLLECTORS,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.COLLECT_BROWSER_HISTORY,
      {
        type: FlowType.COLLECT_BROWSER_HISTORY,
        friendlyName: 'Collect browser history',
        description:
          'Collect browsing and download history from Chromium-based browsers (like Chrome and Edge), Firefox, Internet Explorer & Safari',
        category: FlowCategory.BROWSER,
        favorite: true,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.COLLECT_CLOUD_VM_METADATA,
      {
        type: FlowType.COLLECT_CLOUD_VM_METADATA,
        friendlyName: 'Collect Cloud VM metadata',
        description: 'Collects metadata about a Cloud VM',
        category: FlowCategory.COLLECTORS,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.COLLECT_DISTRO_INFO,
      {
        type: FlowType.COLLECT_DISTRO_INFO,
        friendlyName: 'Collect distro info',
        description: 'Collects distro information from the client',
        category: FlowCategory.COLLECTORS,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.COLLECT_FILES_BY_KNOWN_PATH,
      {
        type: FlowType.COLLECT_FILES_BY_KNOWN_PATH,
        friendlyName: 'Collect files from exact paths',
        description: 'Collect one or more files based on their absolute paths',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.COLLECT_HARDWARE_INFO,
      {
        type: FlowType.COLLECT_HARDWARE_INFO,
        friendlyName: 'Collect hardware info',
        description: 'Collects hardware information from the client',
        category: FlowCategory.HARDWARE,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.COLLECT_INSTALLED_SOFTWARE,
      {
        type: FlowType.COLLECT_INSTALLED_SOFTWARE,
        friendlyName: 'Collect installed software',
        description: 'Collects installed software from the client',
        category: FlowCategory.COLLECTORS,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.COLLECT_LARGE_FILE_FLOW,
      {
        type: FlowType.COLLECT_LARGE_FILE_FLOW,
        friendlyName: 'Collect large file',
        description: 'Collects a file to a Google Cloud storage bucket',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.COLLECT_MULTIPLE_FILES,
      {
        type: FlowType.COLLECT_MULTIPLE_FILES,
        friendlyName: 'Collect files by search criteria',
        description:
          'Search for and collect files based on their path, content or stat',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.DELETE_GRR_TEMP_FILES,
      {
        type: FlowType.DELETE_GRR_TEMP_FILES,
        friendlyName: 'Delete GRR temp files',
        description: 'Delete GRR temp files',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.DUMP_PROCESS_MEMORY,
      {
        type: FlowType.DUMP_PROCESS_MEMORY,
        friendlyName: 'Dump process memory',
        description: 'Dump the process memory of one ore more processes',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.EXECUTE_PYTHON_HACK,
      {
        type: FlowType.EXECUTE_PYTHON_HACK,
        friendlyName: 'Execute Python hack',
        description: 'Execute a one-off Python script',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: true,
        hidden: false,
      },
    ],
    [
      FlowType.FILE_FINDER,
      {
        type: FlowType.FILE_FINDER,
        friendlyName: 'File finder',
        description: 'Finds files on the client',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.GET_CROWDSTRIKE_AGENT_ID,
      {
        type: FlowType.GET_CROWDSTRIKE_AGENT_ID,
        friendlyName: 'Get CrowdStrike agent identifier',
        description: 'Get the CrowdStrike agent identifier',
        category: FlowCategory.COLLECTORS,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.GET_MBR,
      {
        type: FlowType.GET_MBR,
        friendlyName: 'Get MBR',
        description: 'Dump the Master Boot Record on Windows',
        category: FlowCategory.HARDWARE,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.GET_MEMORY_SIZE,
      {
        type: FlowType.GET_MEMORY_SIZE,
        friendlyName: 'Get memory size',
        description: 'Get the size of the memory',
        category: FlowCategory.HARDWARE,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.HASH_MULTIPLE_FILES,
      {
        type: FlowType.HASH_MULTIPLE_FILES,
        friendlyName: 'Hash files by search criteria',
        description:
          'Search for and collect file hashes based on their path, content or stat',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.INTERROGATE,
      {
        type: FlowType.INTERROGATE,
        friendlyName: 'Interrogate',
        description:
          'Collect general metadata about the client (e.g. operating system details, users, ...)',
        category: FlowCategory.ADMINISTRATIVE,
        favorite: true,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.KILL,
      {
        type: FlowType.KILL,
        friendlyName: 'Kill GRR',
        description: 'Kill GRR process',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW,
      {
        type: FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW,
        friendlyName: 'Knowledge base initialization',
        description: 'Initialize the knowledge base',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.LAUNCH_BINARY,
      {
        type: FlowType.LAUNCH_BINARY,
        friendlyName: 'Execute binary hack',
        description: 'Executes a binary from an allowlisted path',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: true,
        hidden: false,
      },
    ],
    [
      FlowType.LIST_CONTAINERS,
      {
        type: FlowType.LIST_CONTAINERS,
        friendlyName: 'List containers',
        description: 'Lists containers on the client',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.LIST_DIRECTORY,
      {
        type: FlowType.LIST_DIRECTORY,
        friendlyName: 'List directory',
        description: 'Lists and stats all immediate files in directory',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.LIST_NAMED_PIPES_FLOW,
      {
        type: FlowType.LIST_NAMED_PIPES_FLOW,
        friendlyName: 'List named pipes',
        description: 'Collects metadata about named pipes open on the system',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.LIST_PROCESSES,
      {
        type: FlowType.LIST_PROCESSES,
        friendlyName: 'List processes',
        description: 'Collects metadata about running processes',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.LIST_RUNNING_SERVICES,
      {
        type: FlowType.LIST_RUNNING_SERVICES,
        friendlyName: 'List running services',
        description: 'Collects metadata about running services',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.LIST_VOLUME_SHADOW_COPIES,
      {
        type: FlowType.LIST_VOLUME_SHADOW_COPIES,
        friendlyName: 'List volume shadow copies',
        description: 'Lists volume shadow copies on the client',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.MULTI_GET_FILE,
      {
        type: FlowType.MULTI_GET_FILE,
        friendlyName: 'MultiGetFile',
        description: 'Collects multiple files from the client',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.NETSTAT,
      {
        type: FlowType.NETSTAT,
        friendlyName: 'Netstat',
        description: 'Enumerate all open network connections',
        category: FlowCategory.NETWORK,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.ONLINE_NOTIFICATION,
      {
        type: FlowType.ONLINE_NOTIFICATION,
        friendlyName: 'Online notification',
        description: 'Notify via email when the client comes online',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.OS_QUERY_FLOW,
      {
        type: FlowType.OS_QUERY_FLOW,
        friendlyName: 'Osquery',
        description: 'Execute a query using osquery',
        category: FlowCategory.COLLECTORS,
        favorite: true,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.READ_LOW_LEVEL,
      {
        type: FlowType.READ_LOW_LEVEL,
        friendlyName: 'Read raw bytes from device',
        description:
          'Read raw data from a device - e.g. from a particular disk sector',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.RECURSIVE_LIST_DIRECTORY,
      {
        type: FlowType.RECURSIVE_LIST_DIRECTORY,
        friendlyName: 'Recursive list directory',
        description: 'Lists and stats all files in directory',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.REGISTRY_FINDER,
      {
        type: FlowType.REGISTRY_FINDER,
        friendlyName: 'Registry finder',
        description: 'Finds registry keys on the client',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.STAT_MULTIPLE_FILES,
      {
        type: FlowType.STAT_MULTIPLE_FILES,
        friendlyName: 'Stat files by search criteria',
        description:
          'Search for and collect file stats based on their path, content or stat. Can also be used for recursive directory listing.',
        category: FlowCategory.FILESYSTEM,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.TIMELINE_FLOW,
      {
        type: FlowType.TIMELINE_FLOW,
        friendlyName: 'Collect path timeline',
        description:
          'Collect metadata information for all files under the specified directory',
        category: FlowCategory.FILESYSTEM,
        favorite: true,
        restricted: false,
        hidden: false,
      },
    ],
    [
      FlowType.UPDATE_CLIENT,
      {
        type: FlowType.UPDATE_CLIENT,
        friendlyName: 'Update client',
        description: 'Update the client',
        category: FlowCategory.ADMINISTRATIVE,
        restricted: false,
        hidden: true,
      },
    ],
    [
      FlowType.YARA_PROCESS_SCAN,
      {
        type: FlowType.YARA_PROCESS_SCAN,
        friendlyName: 'Scan process memory with YARA',
        description: 'Scan and optionally dump process memory using Yara',
        category: FlowCategory.PROCESSES,
        restricted: false,
        hidden: false,
      },
    ],
  ],
);
