import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {PathSpecPathType} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectionResults} from './collection_results';
import {CollectionResultsHarness} from './testing/collection_results_harness';

initTestEnvironment();

async function createComponent(
  collectionResults: Map<PayloadType, readonly CollectionResult[]> | undefined,
) {
  const fixture = TestBed.createComponent(CollectionResults);
  fixture.componentRef.setInput('collectionResultsByType', collectionResults);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectionResultsHarness,
  );
  return {fixture, harness};
}

describe('Collection Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectionResults, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent(new Map([]));
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows no results if there are no results', async () => {
    const {harness} = await createComponent(new Map([]));

    expect(await harness.clientSnapshots()).toBeFalsy();
    expect(await harness.collectBrowserHistoryResults()).toBeFalsy();
    expect(await harness.collectCloudVmMetadataResults()).toBeFalsy();
    expect(await harness.collectDistroInfoResults()).toBeFalsy();
    expect(await harness.collectFilesByKnownPathResults()).toBeFalsy();
    expect(await harness.collectLargeFileFlowResults()).toBeFalsy();
    expect(await harness.collectMultipleFilesResults()).toBeFalsy();
    expect(await harness.executeBinaryResponses()).toBeFalsy();
    expect(await harness.executePythonHackResults()).toBeFalsy();
    expect(await harness.executeResponseResults()).toBeFalsy();
    expect(await harness.fileFinderResults()).toBeFalsy();
    expect(await harness.getCrowdstrikeAgentIdResults()).toBeFalsy();
    expect(await harness.getMemorySizeResults()).toBeFalsy();
    expect(await harness.hardwareInfos()).toBeFalsy();
    expect(await harness.knowledgeBases()).toBeFalsy();
    expect(await harness.listContainersFlowResults()).toBeFalsy();
    expect(await harness.networkConnections()).toBeFalsy();
    expect(await harness.osqueryResults()).toBeFalsy();
    expect(await harness.processes()).toBeFalsy();
    expect(await harness.readLowLevelFlowResults()).toBeFalsy();
    expect(await harness.softwarePackagez()).toBeFalsy();
    expect(await harness.statEntryResults()).toBeFalsy();
    expect(await harness.users()).toBeFalsy();
    expect(await harness.yaraProcessDumpResponses()).toBeFalsy();
    expect(await harness.yaraProcessScanMatches()).toBeFalsy();
  });

  it('shows client snapshots', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.CLIENT_SNAPSHOT,
          [
            newFlowResult({
              payloadType: PayloadType.CLIENT_SNAPSHOT,
              payload: {
                clientId: 'C.1234',
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.clientSnapshots()).toBeTruthy();
  });

  it('shows collect browser history results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectBrowserHistoryResults()).toBeTruthy();
  });

  it('shows collect cloud vm metadata results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectCloudVmMetadataResults()).toBeTruthy();
  });

  it('shows collect distro info results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_DISTRO_INFO_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_DISTRO_INFO_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectDistroInfoResults()).toBeTruthy();
  });

  it('shows collect files by known path results', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_FILES_BY_KNOWN_PATH_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_FILES_BY_KNOWN_PATH_RESULT,
              payload: {
                stat: {
                  pathspec: {
                    path: '/foo',
                    pathtype: PathSpecPathType.OS,
                  },
                },
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectFilesByKnownPathResults()).toBeTruthy();
  }));

  it('shows collect large file flow results', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_LARGE_FILE_FLOW_RESULT,
              payload: {
                sessionUri: 'session-uri',
                totalBytesSent: '100',
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectLargeFileFlowResults()).toBeTruthy();
  }));

  it('shows collect multiple files results', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.COLLECT_MULTIPLE_FILES_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.COLLECT_MULTIPLE_FILES_RESULT,
              payload: {
                stat: {
                  pathspec: {
                    path: '/foo',
                    pathtype: PathSpecPathType.OS,
                  },
                },
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.collectMultipleFilesResults()).toBeTruthy();
  }));

  it('shows execute binary responses', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.EXECUTE_BINARY_RESPONSE,
          [
            newFlowResult({
              payloadType: PayloadType.EXECUTE_BINARY_RESPONSE,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.executeBinaryResponses()).toBeTruthy();
  });

  it('shows execute python hack results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.EXECUTE_PYTHON_HACK_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.EXECUTE_PYTHON_HACK_RESULT,
              payload: {
                stdout: 'stdout',
                stderr: 'stderr',
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.executePythonHackResults()).toBeTruthy();
  });

  it('shows execute response results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.EXECUTE_RESPONSE,
          [
            newFlowResult({
              payloadType: PayloadType.EXECUTE_RESPONSE,
              payload: {request: {}},
            }),
          ],
        ],
      ]),
    );

    expect(await harness.executeResponseResults()).toBeTruthy();
  });

  it('shows file finder results', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.FILE_FINDER_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.FILE_FINDER_RESULT,
              payload: {
                statEntry: {
                  pathspec: {
                    path: '/foo',
                    pathtype: PathSpecPathType.OS,
                  },
                },
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.fileFinderResults()).toBeTruthy();
  }));

  it('shows get crowdstrike agent id results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.GET_CROWDSTRIKE_AGENT_ID_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.getCrowdstrikeAgentIdResults()).toBeTruthy();
  });

  it('shows get memory size results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.GET_MEMORY_SIZE_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.GET_MEMORY_SIZE_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.getMemorySizeResults()).toBeTruthy();
  });

  it('shows hardware infos', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.HARDWARE_INFO,
          [newFlowResult({payloadType: PayloadType.HARDWARE_INFO})],
        ],
      ]),
    );

    expect(await harness.hardwareInfos()).toBeTruthy();
  });

  it('shows knowledge bases', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.KNOWLEDGE_BASE,
          [newFlowResult({payloadType: PayloadType.KNOWLEDGE_BASE})],
        ],
      ]),
    );

    expect(await harness.knowledgeBases()).toBeTruthy();
  });

  it('shows list containers flow results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.LIST_CONTAINERS_FLOW_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.LIST_CONTAINERS_FLOW_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.listContainersFlowResults()).toBeTruthy();
  });

  it('shows network connections', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.NETWORK_CONNECTION,
          [newFlowResult({payloadType: PayloadType.NETWORK_CONNECTION})],
        ],
      ]),
    );

    expect(await harness.networkConnections()).toBeTruthy();
  });

  it('shows osquery results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.OSQUERY_RESULT,
          [newFlowResult({payloadType: PayloadType.OSQUERY_RESULT})],
        ],
      ]),
    );

    expect(await harness.osqueryResults()).toBeTruthy();
  });

  it('shows processes', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.PROCESS,
          [
            newFlowResult({
              payloadType: PayloadType.PROCESS,
              payload: {pid: 123},
            }),
          ],
        ],
      ]),
    );

    expect(await harness.processes()).toBeTruthy();
  }));

  it('shows read low level flow results', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
          [
            newFlowResult({
              payloadType: PayloadType.READ_LOW_LEVEL_FLOW_RESULT,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.readLowLevelFlowResults()).toBeTruthy();
  });

  it('shows software packagez', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.SOFTWARE_PACKAGES,
          [newFlowResult({payloadType: PayloadType.SOFTWARE_PACKAGES})],
        ],
      ]),
    );

    expect(await harness.softwarePackagez()).toBeTruthy();
  });

  it('shows stat entry results', fakeAsync(async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.STAT_ENTRY,
          [
            newFlowResult({
              payloadType: PayloadType.STAT_ENTRY,
              payload: {
                pathspec: {
                  path: '/foo',
                  pathtype: PathSpecPathType.OS,
                },
              },
            }),
          ],
        ],
      ]),
    );

    expect(await harness.statEntryResults()).toBeTruthy();
  }));

  it('shows users', async () => {
    const {harness} = await createComponent(
      new Map([
        [PayloadType.USER, [newFlowResult({payloadType: PayloadType.USER})]],
      ]),
    );

    expect(await harness.users()).toBeTruthy();
  });

  it('shows yara process dump responses', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.YARA_PROCESS_DUMP_RESPONSE,
          [
            newFlowResult({
              payloadType: PayloadType.YARA_PROCESS_DUMP_RESPONSE,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.yaraProcessDumpResponses()).toBeTruthy();
  });

  it('shows yara process scan matches', async () => {
    const {harness} = await createComponent(
      new Map([
        [
          PayloadType.YARA_PROCESS_SCAN_MATCH,
          [
            newFlowResult({
              payloadType: PayloadType.YARA_PROCESS_SCAN_MATCH,
            }),
          ],
        ],
      ]),
    );

    expect(await harness.yaraProcessScanMatches()).toBeTruthy();
  });
});
