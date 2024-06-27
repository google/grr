import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {
  ApiFlowState,
  ApiHuntState,
  ForemanClientRuleSet,
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  OutputPluginDescriptor,
} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {
  HttpApiServiceMock,
  mockHttpApiService,
} from '../lib/api/http_api_service_test_util';
import {translateFlow} from '../lib/api_translation/flow';
import {Flow, FlowState, FlowWithDescriptor} from '../lib/models/flow';
import {SafetyLimits} from '../lib/models/hunt';
import {newFlow, newFlowDescriptorMap} from '../lib/models/model_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from './config_global_store_test_util';
import {NewHuntLocalStore} from './new_hunt_local_store';

initTestEnvironment();

describe('NewHuntLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let newHuntLocalStore: NewHuntLocalStore;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        NewHuntLocalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
        {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    newHuntLocalStore = TestBed.inject(NewHuntLocalStore);
  });

  it('verifies access and fetches flow on flowWithDescriptor$ subscription', fakeAsync(() => {
    newHuntLocalStore.selectOriginalFlow('C.1234', 'abcd');
    const sub = newHuntLocalStore.flowWithDescriptor$.subscribe();
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
          category: 'b',
          defaultArgs: {},
        },
        {
          name: 'GetFile',
          friendlyName: 'Get the specified file',
          category: 'a',
          defaultArgs: {},
        },
      ),
    );
    httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(true);
    expect(httpApiService.subscribeToVerifyClientAccess).toHaveBeenCalledWith(
      'C.1234',
    );
    expect(httpApiService.fetchFlow).toHaveBeenCalledWith('C.1234', 'abcd');
    sub.unsubscribe();
  }));

  it('does not fetch flow when no access', fakeAsync(() => {
    newHuntLocalStore.selectOriginalFlow('C.1234', 'abcd');
    const sub = newHuntLocalStore.flowWithDescriptor$.subscribe();
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
          category: 'b',
          defaultArgs: {},
        },
        {
          name: 'GetFile',
          friendlyName: 'Get the specified file',
          category: 'a',
          defaultArgs: {},
        },
      ),
    );
    httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(false);
    expect(httpApiService.subscribeToVerifyClientAccess).toHaveBeenCalledWith(
      'C.1234',
    );
    expect(httpApiService.fetchFlow).not.toHaveBeenCalled();
    sub.unsubscribe();
  }));

  it('emits Flow', fakeAsync(async () => {
    const flow: Flow = newFlow({
      flowId: 'abcd',
      clientId: 'C.1234',
      lastActiveAt: new Date(999),
      startedAt: new Date(789),
      creator: 'morty',
      name: 'GetFile',
      state: FlowState.RUNNING,
      isRobot: false,
    });
    const expected: FlowWithDescriptor = {
      flow,
      descriptor: {
        name: 'GetFile',
        friendlyName: 'Get the specified file',
        blockHuntCreation: false,
        category: 'a',
        defaultArgs: {},
      },
      flowArgType: undefined,
    };
    newHuntLocalStore.selectOriginalFlow('C.1234', 'abcd');
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
          category: 'b',
          blockHuntCreation: false,
          defaultArgs: {},
        },
        {
          name: 'GetFile',
          friendlyName: 'Get the specified file',
          category: 'a',
          blockHuntCreation: false,
          defaultArgs: {},
        },
      ),
    );
    const promise = firstValueFrom(
      newHuntLocalStore.flowWithDescriptor$.pipe(filter(isNonNull)),
    );
    httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(true);
    httpApiService.mockedObservables.fetchFlow.next({
      flowId: 'abcd',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '789000',
      creator: 'morty',
      name: 'GetFile',
      state: ApiFlowState.RUNNING,
      isRobot: false,
    });

    expect(httpApiService.fetchFlow).toHaveBeenCalledWith('C.1234', 'abcd');

    expect(await promise).toEqual(expected);
  }));

  it('updates safety limits', fakeAsync(async () => {
    const expected: Partial<SafetyLimits> = {
      clientRate: 200.0,
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
    };

    configGlobalStore.mockedObservables.uiConfig$.next({
      defaultHuntRunnerArgs: {
        clientRate: 200.0,
        crashLimit: '100',
        avgResultsPerClientLimit: '1000',
        avgCpuSecondsPerClientLimit: '60',
        avgNetworkBytesPerClientLimit: '10485760',
      },
    });

    expect(
      await firstValueFrom(newHuntLocalStore.defaultSafetyLimits$),
    ).toEqual(jasmine.objectContaining(expected));
  }));

  it('updates client rule set', fakeAsync(async () => {
    const expected: ForemanClientRuleSet = {
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [
        {ruleType: ForemanClientRuleType.OS},
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {labelNames: ['some label']},
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {attributeRegex: 'some regex'},
        },
      ],
    };

    configGlobalStore.mockedObservables.uiConfig$.next({
      defaultHuntRunnerArgs: {
        clientRuleSet: {
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [
            {
              ruleType: ForemanClientRuleType.LABEL,
              label: {labelNames: ['some label']},
            },
            {
              ruleType: ForemanClientRuleType.REGEX,
              regex: {attributeRegex: 'some regex'},
            },
          ],
        },
      },
    });

    expect(
      await firstValueFrom(newHuntLocalStore.defaultClientRuleSet$),
    ).toEqual(jasmine.objectContaining(expected));
  }));

  it('emits EMPTY presubmit options - no config', fakeAsync(async () => {
    configGlobalStore.mockedObservables.uiConfig$.next({
      huntConfig: {
        makeDefaultExcludeLabelsAPresubmitCheck: false,
      },
    });
    newHuntLocalStore.setCurrentDescription('');

    expect(
      await firstValueFrom(newHuntLocalStore.presubmitOptions$),
    ).toBeFalsy();
  }));

  it('emits EMPTY presubmit options - force tag', fakeAsync(async () => {
    configGlobalStore.mockedObservables.uiConfig$.next({
      huntConfig: {
        makeDefaultExcludeLabelsAPresubmitCheck: true,
      },
    });
    newHuntLocalStore.setCurrentDescription('something FORCE another thing');

    expect(
      await firstValueFrom(newHuntLocalStore.presubmitOptions$),
    ).toBeFalsy();
  }));

  it('emits presubmit options', fakeAsync(async () => {
    configGlobalStore.mockedObservables.uiConfig$.next({
      huntConfig: {
        makeDefaultExcludeLabelsAPresubmitCheck: true,
        defaultExcludeLabels: ['exterminate', 'exterminate'],
        presubmitWarningMessage: 'nonono',
      },
    });
    newHuntLocalStore.setCurrentDescription('no skip tag');

    const presubmitOptions = await firstValueFrom(
      newHuntLocalStore.presubmitOptions$,
    );
    expect(presubmitOptions?.markdownText).toContain('nonono');
    expect(presubmitOptions?.expectedExcludedLabels).toEqual([
      'exterminate',
      'exterminate',
    ]);
  }));

  it('runs a hunt', fakeAsync(() => {
    const safetyLimits: SafetyLimits = {
      clientRate: 200.0,
      clientLimit: BigInt(123),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
      perClientCpuLimit: BigInt(100),
      perClientNetworkBytesLimit: BigInt(1024),
      expiryTime: BigInt(3600),
    };

    const rules: ForemanClientRuleSet = {
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
    };

    const outputPlugins: readonly OutputPluginDescriptor[] = [
      {
        pluginName: 'some plugin',
      },
    ];

    newHuntLocalStore.selectOriginalHunt('H5678');
    newHuntLocalStore.selectOriginalFlow('C.1234', 'abcd');
    const sub = newHuntLocalStore.flowWithDescriptor$.subscribe();
    const descriptorMap = newFlowDescriptorMap(
      {
        name: 'ClientFileFinder',
        friendlyName: 'Client Side File Finder',
      },
      {
        name: 'GetFile',
        friendlyName: 'Get the specified file',
      },
    );
    configGlobalStore.mockedObservables.flowDescriptors$.next(descriptorMap);
    const apiFlow = {
      flowId: 'abcd',
      clientId: 'C.1234',
      lastActiveAt: '999000',
      startedAt: '789000',
      creator: 'morty',
      name: 'GetFile',
      state: ApiFlowState.RUNNING,
      isRobot: false,
    };
    httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(true);
    httpApiService.mockedObservables.fetchFlow.next(apiFlow);
    const expectedFlowWithDescriptors = {
      flow: translateFlow(apiFlow),
      descriptor: descriptorMap.get('GetFile'),
      flowArgType: undefined,
    };

    newHuntLocalStore.runHunt('new hunt', safetyLimits, rules, outputPlugins);
    expect(httpApiService.createHunt).toHaveBeenCalledWith(
      'new hunt',
      expectedFlowWithDescriptors,
      null,
      safetyLimits,
      rules,
      outputPlugins,
      'H5678',
    );
    sub.unsubscribe();
  }));

  it('calls the fetchHunt API after selectOriginalHunt', fakeAsync(() => {
    const sub = newHuntLocalStore.originalHunt$.subscribe();
    newHuntLocalStore.selectOriginalHunt('H1234');

    expect(httpApiService.fetchHunt).toHaveBeenCalledWith('H1234');
    sub.unsubscribe();
  }));

  it('fetches flow if hunt has original flow set', fakeAsync(async () => {
    newHuntLocalStore.selectOriginalHunt('H1234');
    const promise = firstValueFrom(
      newHuntLocalStore.originalHunt$.pipe(filter(isNonNull)),
    );

    expect(httpApiService.fetchHunt).toHaveBeenCalledWith('H1234');
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap(
        {
          name: 'ClientFileFinder',
          friendlyName: 'Client Side File Finder',
        },
        {
          name: 'GetFile',
          friendlyName: 'Get the specified file',
        },
      ),
    );
    httpApiService.mockedObservables.fetchHunt.next({
      huntId: 'H1234',
      originalObject: {
        flowReference: {
          flowId: 'abcd',
          clientId: 'C.1234',
        },
      },
      name: 'Name',
      created: '123456789',
      creator: 'foo',
      state: ApiHuntState.STARTED,
      huntRunnerArgs: {clientRate: 0},
    });

    // Emits initial hunt arguments
    expect(await promise).toEqual(
      jasmine.objectContaining({
        huntId: 'H1234',
        name: 'Name',
        creator: 'foo',
        flowReference: {
          flowId: 'abcd',
          clientId: 'C.1234',
        },
      }),
    );

    // Selects original flow based on reference
    httpApiService.mockedObservables.subscribeToVerifyClientAccess.next(true);
    expect(httpApiService.subscribeToVerifyClientAccess).toHaveBeenCalledWith(
      'C.1234',
    );
    expect(httpApiService.fetchFlow).toHaveBeenCalledWith('C.1234', 'abcd');
  }));
});
