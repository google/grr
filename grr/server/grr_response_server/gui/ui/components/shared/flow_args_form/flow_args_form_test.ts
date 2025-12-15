import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowType} from '../../../lib/models/flow';
import {ClientStore} from '../../../store/client_store';
import {GlobalStore} from '../../../store/global_store';
import {
  newClientStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FlowArgsForm} from './flow_args_form';
import {FlowArgsFormHarness} from './testing/flow_args_form_harness';

initTestEnvironment();

async function createComponent(flowType: FlowType, flowArgs?: {}) {
  const fixture = TestBed.createComponent(FlowArgsForm);
  fixture.componentRef.setInput('flowType', flowType);
  if (flowArgs) {
    fixture.componentRef.setInput('fixedFlowArgs', flowArgs);
  }
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowArgsFormHarness,
  );
  return {fixture, harness};
}

describe('Flow Args Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, FlowArgsForm],
      providers: [
        {provide: ClientStore, useValue: newClientStoreMock()},
        {provide: GlobalStore, useValue: newGlobalStoreMock()},
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const fixture = TestBed.createComponent(FlowArgsForm);
    expect(fixture.componentInstance).toBeDefined();
    expect(fixture.componentInstance).toBeInstanceOf(FlowArgsForm);
  });

  it('renders ArtifactCollectorFlowForm', async () => {
    const {harness} = await createComponent(FlowType.ARTIFACT_COLLECTOR_FLOW);
    expect(await harness.artifactCollectorFlowForm()).toBeDefined();
  });
  it('renders ClientRegistryFinderForm', async () => {
    const {harness} = await createComponent(FlowType.CLIENT_REGISTRY_FINDER);
    expect(await harness.clientRegistryFinderForm()).toBeDefined();
  });
  it('renders CollectBrowserHistoryForm', async () => {
    const {harness} = await createComponent(FlowType.COLLECT_BROWSER_HISTORY);
    expect(await harness.collectBrowserHistoryForm()).toBeDefined();
  });
  it('renders CollectFilesByKnownPathForm', async () => {
    const {harness} = await createComponent(
      FlowType.COLLECT_FILES_BY_KNOWN_PATH,
    );
    expect(await harness.collectFilesByKnownPathForm()).toBeDefined();
  });
  it('renders CollectLargeFileFlowForm', async () => {
    const {harness} = await createComponent(FlowType.COLLECT_LARGE_FILE_FLOW);
    expect(await harness.collectLargeFileFlowForm()).toBeDefined();
  });

  it('renders CollectMultipleFilesForm', async () => {
    const {harness} = await createComponent(FlowType.COLLECT_MULTIPLE_FILES);
    expect(await harness.collectMultipleFilesForm()).toBeDefined();
  });
  it('renders DumpProcessMemoryForm', async () => {
    const {harness} = await createComponent(FlowType.DUMP_PROCESS_MEMORY);
    expect(await harness.dumpProcessMemoryForm()).toBeDefined();
  });
  it('renders ExecutePythonHackForm', async () => {
    const {harness} = await createComponent(FlowType.EXECUTE_PYTHON_HACK);
    expect(await harness.executePythonHackForm()).toBeDefined();
  });
  it('renders GetMBRForm', async () => {
    const {harness} = await createComponent(FlowType.GET_MBR);
    expect(await harness.getMBRForm()).toBeDefined();
  });
  it('renders HashMultipleFilesForm', async () => {
    const {harness} = await createComponent(FlowType.HASH_MULTIPLE_FILES);
    expect(await harness.hashMultipleFilesForm()).toBeDefined();
  });
  it('renders InterrogateForm', async () => {
    const {harness} = await createComponent(FlowType.INTERROGATE);
    expect(await harness.interrogateForm()).toBeDefined();
  });
  it('renders KillGrrForm', async () => {
    const {harness} = await createComponent(FlowType.KILL);
    expect(await harness.killGrrForm()).toBeDefined();
  });
  it('renders LaunchBinaryForm', async () => {
    const {harness} = await createComponent(FlowType.LAUNCH_BINARY);
    expect(await harness.launchBinaryForm()).toBeDefined();
  });
  it('renders ListDirectoryForm', async () => {
    const {harness} = await createComponent(FlowType.LIST_DIRECTORY);
    expect(await harness.listDirectoryForm()).toBeDefined();
  });
  it('renders ListNamedPipesForm', async () => {
    const {harness} = await createComponent(FlowType.LIST_NAMED_PIPES_FLOW);
    expect(await harness.listNamedPipesForm()).toBeDefined();
  });
  it('renders ListProcessesForm', async () => {
    const {harness} = await createComponent(FlowType.LIST_PROCESSES);
    expect(await harness.listProcessesForm()).toBeDefined();
  });
  it('renders NetstatForm', async () => {
    const {harness} = await createComponent(FlowType.NETSTAT);
    expect(await harness.netstatForm()).toBeDefined();
  });
  it('renders OnlineNotificationForm', async () => {
    const {harness} = await createComponent(FlowType.ONLINE_NOTIFICATION);
    expect(await harness.onlineNotificationForm()).toBeDefined();
  });
  it('renders OsqueryForm', async () => {
    const {harness} = await createComponent(FlowType.OS_QUERY_FLOW);
    expect(await harness.osqueryForm()).toBeDefined();
  });
  it('renders ReadLowLevelForm', async () => {
    const {harness} = await createComponent(FlowType.READ_LOW_LEVEL);
    expect(await harness.readLowLevelForm()).toBeDefined();
  });
  it('renders StatMultipleFilesForm', async () => {
    const {harness} = await createComponent(FlowType.STAT_MULTIPLE_FILES);
    expect(await harness.statMultipleFilesForm()).toBeDefined();
  });
  it('renders TimelineForm', async () => {
    const {harness} = await createComponent(FlowType.TIMELINE_FLOW);
    expect(await harness.timelineForm()).toBeDefined();
  });
  it('renders YaraProcessScanForm', async () => {
    const {harness} = await createComponent(FlowType.YARA_PROCESS_SCAN);
    expect(await harness.yaraProcessScanForm()).toBeDefined();
  });
});
