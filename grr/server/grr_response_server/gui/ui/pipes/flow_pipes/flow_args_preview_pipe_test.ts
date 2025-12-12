import {
  ArtifactCollectorFlowArgs,
  Browser,
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
  NetworkConnectionState,
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
import {FlowArgsPreviewPipe} from './flow_args_preview_pipe';

describe('Flow Args Preview Pipe', () => {
  const pipe = new FlowArgsPreviewPipe();

  it('return empty string for undefined flow type', () => {
    expect(pipe.transform({}, undefined)).toEqual('');
  });

  it('returns the flow args preview for artifact collector flow', () => {
    const flowType = FlowType.ARTIFACT_COLLECTOR_FLOW;
    const flowArgs: ArtifactCollectorFlowArgs = {
      artifactList: ['artifact1', 'artifact2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('artifact1, artifact2');
  });

  it('returns the flow args preview for client file finder flow', () => {
    const flowType = FlowType.CLIENT_FILE_FINDER;
    const flowArgs: FileFinderArgs = {
      paths: ['/path/to/file', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file, /path/to/file2',
    );
  });

  it('returns the flow args preview for client registry finder flow', () => {
    const flowType = FlowType.CLIENT_REGISTRY_FINDER;
    const flowArgs: RegistryFinderArgs = {
      keysPaths: ['/registry/path/*', '/registry/path_2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/registry/path/*, /registry/path_2',
    );
  });

  it('returns the flow args preview for collect browser history flow', () => {
    const flowType = FlowType.COLLECT_BROWSER_HISTORY;
    const flowArgs: CollectBrowserHistoryArgs = {
      browsers: [Browser.CHROMIUM_BASED_BROWSERS, Browser.FIREFOX],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      'CHROMIUM_BASED_BROWSERS, FIREFOX',
    );
  });

  it('returns the flow args preview for collect files by known path flow', () => {
    const flowType = FlowType.COLLECT_FILES_BY_KNOWN_PATH;
    const flowArgs: CollectFilesByKnownPathArgs = {
      paths: ['/path/to/file', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file, /path/to/file2',
    );
  });

  it('returns the flow args preview for collect large file flow', () => {
    const flowType = FlowType.COLLECT_LARGE_FILE_FLOW;
    const flowArgs: CollectLargeFileFlowArgs = {
      pathSpec: {
        path: '/path/to/file',
      },
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/file');
  });

  it('returns the flow args preview for collect multiple files flow', () => {
    const flowType = FlowType.COLLECT_MULTIPLE_FILES;
    const flowArgs: CollectMultipleFilesArgs = {
      pathExpressions: ['/path/to/file/*', '/path/to/file2/*'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file/*, /path/to/file2/*',
    );
  });

  it('return the flow args preview for execute python hack flow', () => {
    const flowType = FlowType.EXECUTE_PYTHON_HACK;
    const flowArgs: ExecutePythonHackArgs = {
      hackName: 'test_hack',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('test_hack');
  });

  it('return the flow args preview for file finder flow', () => {
    const flowType = FlowType.FILE_FINDER;
    const flowArgs: FileFinderArgs = {
      paths: ['/path/to/file', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file, /path/to/file2',
    );
  });

  it('returns the flow args preview for hash multiple files flow', () => {
    const flowType = FlowType.HASH_MULTIPLE_FILES;
    const flowArgs: HashMultipleFilesArgs = {
      pathExpressions: ['/path/to/file/*', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file/*, /path/to/file2',
    );
  });

  it('returns the flow args preview for launch binary flow', () => {
    const flowType = FlowType.LAUNCH_BINARY;
    const flowArgs: LaunchBinaryArgs = {
      binary: '/path/to/binary',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/binary');
  });

  it('returns the flow args preview for list directory flow', () => {
    const flowType = FlowType.LIST_DIRECTORY;
    const flowArgs: ListDirectoryArgs = {
      pathspec: {
        path: '/path/to/directory',
      },
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/directory');
  });

  it('returns the flow args preview for list processes flow', () => {
    const flowType = FlowType.LIST_PROCESSES;
    const flowArgs: ListProcessesArgs = {
      filenameRegex: '/path/to/file',
      fetchBinaries: true,
      connectionStates: [
        NetworkConnectionState.CLOSED,
        NetworkConnectionState.ESTABLISHED,
        NetworkConnectionState.UNKNOWN,
      ],
      pids: [12345, 67890],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file - with binaries - CLOSED, ESTABLISHED, UNKNOWN - 12345, 67890',
    );
  });

  it('returns the flow args preview for multi get file flow', () => {
    const flowType = FlowType.MULTI_GET_FILE;
    const flowArgs: MultiGetFileArgs = {
      pathspecs: [
        {
          path: '/path/to/file',
        },
        {
          path: '/path/to/file2',
        },
      ],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file, /path/to/file2',
    );
  });

  it('returns the flow args preview for netstat flow', () => {
    const flowType = FlowType.NETSTAT;
    const flowArgs: NetstatArgs = {
      listeningOnly: true,
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('listening only');
  });

  it('returns the flow args preview for OS query flow', () => {
    const flowType = FlowType.OS_QUERY_FLOW;
    const flowArgs: OsqueryFlowArgs = {
      query: 'SELECT * FROM test_table',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      'SELECT * FROM test_table',
    );
  });

  it('returns the flow args preview for read low level flow', () => {
    const flowType = FlowType.READ_LOW_LEVEL;
    const flowArgs: ReadLowLevelArgs = {
      path: '/path/to/file',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/file');
  });

  it('returns the flow args preview for recursive list directory flow', () => {
    const flowType = FlowType.RECURSIVE_LIST_DIRECTORY;
    const flowArgs: RecursiveListDirectoryArgs = {
      pathspec: {
        path: '/path/to/directory',
      },
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/directory');
  });

  it('returns the flow args preview for registry finder flow', () => {
    const flowType = FlowType.REGISTRY_FINDER;
    const flowArgs: RegistryFinderArgs = {
      keysPaths: ['/path/to/file/*', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file/*, /path/to/file2',
    );
  });

  it('returns the flow args preview for stat multiple files flow', () => {
    const flowType = FlowType.STAT_MULTIPLE_FILES;
    const flowArgs: StatMultipleFilesArgs = {
      pathExpressions: ['/path/to/file', '/path/to/file2'],
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '/path/to/file, /path/to/file2',
    );
  });

  it('returns the flow args preview for timeline flow', () => {
    const flowType = FlowType.TIMELINE_FLOW;
    const flowArgs: TimelineArgs = {
      root: '/path/to/file',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/file');
  });

  it('returns the flow args preview for update client flow', () => {
    const flowType = FlowType.UPDATE_CLIENT;
    const flowArgs: UpdateClientArgs = {
      binaryPath: '/path/to/binary',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual('/path/to/binary');
  });

  it('returns the flow args preview for yara process dump flow', () => {
    const flowType = FlowType.YARA_PROCESS_SCAN;
    const flowArgs: YaraProcessDumpArgs = {
      pids: ['12345', '67890'],
      processRegex: 'test_process_regex',
    };

    expect(pipe.transform(flowArgs, flowType)).toEqual(
      '12345, 67890 - test_process_regex',
    );
  });

  it('returns empty string for remaining flow types', () => {
    expect(
      pipe.transform(undefined, FlowType.COLLECT_CLOUD_VM_METADATA),
    ).toEqual('');
    expect(pipe.transform(undefined, FlowType.COLLECT_DISTRO_INFO)).toEqual('');
    expect(pipe.transform(undefined, FlowType.COLLECT_HARDWARE_INFO)).toEqual(
      '',
    );
    expect(
      pipe.transform(undefined, FlowType.COLLECT_INSTALLED_SOFTWARE),
    ).toEqual('');
    expect(pipe.transform(undefined, FlowType.DELETE_GRR_TEMP_FILES)).toEqual(
      '',
    );
    expect(pipe.transform(undefined, FlowType.DUMP_PROCESS_MEMORY)).toEqual('');
    expect(
      pipe.transform(undefined, FlowType.GET_CROWDSTRIKE_AGENT_ID),
    ).toEqual('');
    expect(pipe.transform(undefined, FlowType.GET_MBR)).toEqual('');
    expect(pipe.transform(undefined, FlowType.GET_MEMORY_SIZE)).toEqual('');
    expect(pipe.transform(undefined, FlowType.INTERROGATE)).toEqual('');
    expect(pipe.transform(undefined, FlowType.KILL)).toEqual('');
    expect(
      pipe.transform(undefined, FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW),
    ).toEqual('');
    expect(pipe.transform(undefined, FlowType.LIST_CONTAINERS)).toEqual('');
    expect(pipe.transform(undefined, FlowType.LIST_NAMED_PIPES_FLOW)).toEqual(
      '',
    );
    expect(pipe.transform(undefined, FlowType.LIST_RUNNING_SERVICES)).toEqual(
      '',
    );
    expect(
      pipe.transform(undefined, FlowType.LIST_VOLUME_SHADOW_COPIES),
    ).toEqual('');
    expect(pipe.transform(undefined, FlowType.MULTI_GET_FILE)).toEqual('');
    expect(pipe.transform(undefined, FlowType.ONLINE_NOTIFICATION)).toEqual('');
  });
});
