import {TestBed} from '@angular/core/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {ApprovalConfig} from '../lib/models/client';
import {ArtifactDescriptor, Binary, BinaryType} from '../lib/models/flow';
import {
  newArtifactDescriptor,
  newFlowDescriptor,
  newGrrUser,
} from '../lib/models/model_test_util';
import {OutputPluginType} from '../lib/models/output_plugin';
import {initTestEnvironment} from '../testing';
import {GlobalStore} from './global_store';

initTestEnvironment();

describe('GlobalStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        GlobalStore,
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiService,
        },
      ],
      teardown: {destroyAfterEach: false},
    });
  });

  it('fetches all data when `initialize()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.initialize();
    expect(httpApiService.fetchCurrentUser).toHaveBeenCalled();
    expect(httpApiService.listFlowDescriptors).toHaveBeenCalled();
    expect(httpApiService.getArtifactDescriptorMap).toHaveBeenCalled();
    expect(httpApiService.fetchAllClientsLabels).toHaveBeenCalled();
    expect(httpApiService.fetchUiConfig).toHaveBeenCalled();
    expect(httpApiService.fetchApprovalConfig).toHaveBeenCalled();
    expect(httpApiService.fetchExportCommandPrefix).toHaveBeenCalled();
  });

  it('calls api to fetch current user and stores it when `fetchCurrentUser()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchCurrentUser();
    const currentUser = newGrrUser({});
    httpApiService.mockedObservables.fetchCurrentUser.next(currentUser);

    expect(httpApiService.fetchCurrentUser).toHaveBeenCalled();
    expect(store.currentUser()).toEqual(currentUser);
  });

  it('calls api to fetch ui config and stores it when `fetchUiConfig()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchUiConfig();
    const uiConfig = {
      heading: 'heading',
      helpUrl: 'help_url',
      profileImageUrl: 'profile_image_url',
    };
    httpApiService.mockedObservables.fetchUiConfig.next(uiConfig);

    expect(httpApiService.fetchUiConfig).toHaveBeenCalled();
    expect(store.uiConfig()).toEqual(uiConfig);
  });

  it('calls api to fetch approval config and stores it when `fetchApprovalConfig()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchApprovalConfig();
    const approvalConfig: ApprovalConfig = {
      optionalCcEmail: 'test@example.com',
    };
    httpApiService.mockedObservables.fetchApprovalConfig.next(approvalConfig);

    expect(httpApiService.fetchApprovalConfig).toHaveBeenCalled();
    expect(store.approvalConfig()).toEqual(approvalConfig);
  });

  it('calls api to fetch web auth type and stores it when `fetchWebAuthType()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchWebAuthType();
    const webAuthType: string = 'CorpSSOWebAuthManager';
    httpApiService.mockedObservables.fetchWebAuthType.next(webAuthType);

    expect(httpApiService.fetchWebAuthType).toHaveBeenCalled();
    expect(store.webAuthType()).toEqual(webAuthType);
  });

  it('calls api to fetch all labels and stores them when `fetchAllLabels()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchAllLabels();
    const labels = ['label1', 'label2'];
    httpApiService.mockedObservables.fetchAllClientsLabels.next(labels);

    expect(httpApiService.fetchAllClientsLabels).toHaveBeenCalled();
    expect(store.allLabels()).toEqual(labels);
  });

  it('calls api to fetch all flow descriptors and stores them when `fetchAllFlowDescriptors()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchFlowDescriptors();
    const flowDescriptors = [
      newFlowDescriptor({name: 'flow1'}),
      newFlowDescriptor({name: 'flow2'}),
    ];
    httpApiService.mockedObservables.listFlowDescriptors.next(flowDescriptors);

    expect(httpApiService.listFlowDescriptors).toHaveBeenCalled();
    expect(store.flowDescriptors()).toEqual(flowDescriptors);
    expect(store.flowDescriptorsMap()).toEqual(
      new Map(flowDescriptors.map((fd) => [fd.name, fd])),
    );
  });

  it('calls api to fetch all artifact descriptors and stores them when `fetchAllArtifactDescriptors()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.getArtifactDescriptorMap();
    const artifactDescriptorMap = new Map<string, ArtifactDescriptor>([
      ['artifact1', newArtifactDescriptor({name: 'artifact1'})],
      ['artifact2', newArtifactDescriptor({name: 'artifact2'})],
    ]);
    httpApiService.mockedObservables.getArtifactDescriptorMap.next(
      artifactDescriptorMap,
    );

    expect(httpApiService.getArtifactDescriptorMap).toHaveBeenCalled();
    expect(store.artifactDescriptorMap()).toEqual(artifactDescriptorMap);
  });

  it('calls api to fetch all binaries and stores them when `fetchAllBinaries()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchBinaryNames();
    const binaries: Binary[] = [
      {type: BinaryType.PYTHON_HACK, path: 'path1'},
      {type: BinaryType.PYTHON_HACK, path: 'path2'},
    ];
    httpApiService.mockedObservables.listBinaries.next(binaries);

    expect(httpApiService.listBinaries).toHaveBeenCalledWith(false);
    expect(store.binaries()).toEqual(binaries);
  });

  it('calls api to fetch export command prefix and stores it when `fetchExportCommandPrefix()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchExportCommandPrefix();
    const exportCommandPrefix: string = 'export_command_prefix';
    httpApiService.mockedObservables.fetchExportCommandPrefix.next(
      exportCommandPrefix,
    );

    expect(httpApiService.fetchExportCommandPrefix).toHaveBeenCalled();
    expect(store.exportCommandPrefix()).toEqual(exportCommandPrefix);
  });

  it('updates python hacks and executables when binaries are fetched', () => {
    const store = TestBed.inject(GlobalStore);
    expect(store.pythonHacks()).toEqual([]);
    expect(store.executables()).toEqual([]);

    store.fetchBinaryNames();
    const binaries: Binary[] = [
      {type: BinaryType.PYTHON_HACK, path: 'b_python/path'},
      {type: BinaryType.PYTHON_HACK, path: 'a_python/path'},
      {type: BinaryType.EXECUTABLE, path: 'b_executable/path'},
      {type: BinaryType.EXECUTABLE, path: 'a_executable/path'},
    ];
    httpApiService.mockedObservables.listBinaries.next(binaries);

    expect(store.binaries()).toEqual(binaries);
    expect(store.pythonHacks()).toEqual([
      {type: BinaryType.PYTHON_HACK, path: 'a_python/path'},
      {type: BinaryType.PYTHON_HACK, path: 'b_python/path'},
    ]);
    expect(store.executables()).toEqual([
      {type: BinaryType.EXECUTABLE, path: 'a_executable/path'},
      {type: BinaryType.EXECUTABLE, path: 'b_executable/path'},
    ]);
  });

  it('calls api to fetch all output plugin descriptors and stores them when `fetchAllOutputPluginDescriptors()` is called', () => {
    const store = TestBed.inject(GlobalStore);

    store.fetchOutputPluginDescriptors();
    const outputPluginDescriptors = [
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: 'Email output plugin description',
      },
    ];
    httpApiService.mockedObservables.listOutputPluginDescriptors.next(
      outputPluginDescriptors,
    );

    expect(httpApiService.listOutputPluginDescriptors).toHaveBeenCalled();
    expect(store.outputPluginDescriptors()).toEqual(outputPluginDescriptors);
  });
});
