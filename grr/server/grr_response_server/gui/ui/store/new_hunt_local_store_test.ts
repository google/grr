import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {ApiFlowState, ApiHuntApproval, ForemanClientRuleSet, ForemanClientRuleSetMatchMode, OutputPluginDescriptor} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {Flow, FlowState, FlowWithDescriptor} from '../lib/models/flow';
import {SafetyLimits} from '../lib/models/hunt';
import {newFlow, newFlowDescriptorMap} from '../lib/models/model_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from './config_global_store_test_util';
import {NewHuntLocalStore} from './new_hunt_local_store';

initTestEnvironment();


describe('NewHuntLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let newHuntLocalStore: NewHuntLocalStore;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            NewHuntLocalStore,
            {provide: HttpApiService, useFactory: () => httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    newHuntLocalStore = TestBed.inject(NewHuntLocalStore);
  });

  it('calls the fetchFlow API on testFlow$ subscription', fakeAsync(() => {
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
                 friendlyName: 'KeepAlive',
                 category: 'a',
                 defaultArgs: {},
               }));

       expect(httpApiService.fetchFlow).toHaveBeenCalledWith('C.1234', 'abcd');
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
           friendlyName: 'KeepAlive',
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
                 defaultArgs: {},
               },
               {
                 name: 'GetFile',
                 friendlyName: 'KeepAlive',
                 category: 'a',
                 defaultArgs: {},
               }));

       const promise = firstValueFrom(
           newHuntLocalStore.flowWithDescriptor$.pipe(filter(isNonNull)));
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

       expect(await firstValueFrom(newHuntLocalStore.safetyLimits$))
           .toEqual(jasmine.objectContaining(expected));
     }));

  it('runs a hunt', fakeAsync(() => {
       const safetyLimits: SafetyLimits = {
         clientRate: 200.0,
         clientLimit: BigInt(123),
         crashLimit: BigInt(100),
         avgResultsPerClientLimit: BigInt(1000),
         avgCpuSecondsPerClientLimit: BigInt(60),
         avgNetworkBytesPerClientLimit: BigInt(10485760),
         cpuLimit: BigInt(100),
         networkBytesLimit: BigInt(1024),
         expiryTime: BigInt(3600),
       };

       const rules: ForemanClientRuleSet = {
         matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL
       };

       const outputPlugins: ReadonlyArray<OutputPluginDescriptor> = [{
         pluginName: 'some plugin',
       }];

       newHuntLocalStore.selectOriginalFlow('C.1234', 'abcd');
       const sub = newHuntLocalStore.flowWithDescriptor$.subscribe();
       configGlobalStore.mockedObservables.flowDescriptors$.next(
           newFlowDescriptorMap(
               {
                 name: 'ClientFileFinder',
                 friendlyName: 'Client Side File Finder',
               },
               {
                 name: 'GetFile',
                 friendlyName: 'KeepAlive',
               }));
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

       newHuntLocalStore.runHunt(
           'new hunt', safetyLimits, rules, outputPlugins);
       expect(httpApiService.createHunt).toHaveBeenCalled();
       sub.unsubscribe();
     }));

  it('calls request hunt approval', fakeAsync(() => {
       const approvalArgs: ApiHuntApproval = {
         id: 'hunt_1234',
         requestor: 'jake@gmail.com',
       };
       newHuntLocalStore.requestHuntApproval('hunt_1234', approvalArgs);
       expect(httpApiService.requestHuntApproval).toHaveBeenCalled();
     }));
});
