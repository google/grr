import {TestBed} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {FlowType} from '../lib/models/flow';
import {newFlow, newHunt, newSafetyLimits} from '../lib/models/model_test_util';
import {NewFleetCollectionStore} from './new_fleet_collection_store';

describe('NewFleetCollectionStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        NewFleetCollectionStore,
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiService,
        },
      ],
    });
  });

  it('resets the store when `initialize` is called with valid fleet collection reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: {clientId: 'C.123', flowId: '123'},
      originalFleetCollection: newHunt({huntId: '123'}),
      originalFlow: newFlow({clientId: 'C.123', flowId: '123'}),
    });

    store.initialize({huntId: '123'}, undefined);

    expect(store.originalFleetCollectionRef()).toEqual({huntId: '123'});
    expect(store.originalFlowRef()).toBeUndefined();
    expect(store.originalFleetCollection()).toBeUndefined();
    expect(store.originalFlow()).toBeUndefined();
  });

  it('resets the store when `initialize` is called with valid flow reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: {clientId: 'C.123', flowId: '123'},
      originalFleetCollection: newHunt({huntId: '123'}),
      originalFlow: newFlow({clientId: 'C.123', flowId: '123'}),
    });

    store.initialize(undefined, {clientId: 'C.123', flowId: '123'});

    expect(store.originalFleetCollectionRef()).toBeUndefined();
    expect(store.originalFlowRef()).toEqual({clientId: 'C.123', flowId: '123'});
    expect(store.originalFleetCollection()).toBeUndefined();
    expect(store.originalFlow()).toBeUndefined();
  });

  it('throws error when `initialize` is called with both fleet collection and flow reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);

    expect(() => {
      store.initialize({huntId: '123'}, {clientId: 'C.123', flowId: '123'});
    }).toThrowError(
      'Only one reference can be provided to initialize the store.',
    );
  });

  it('throws error when `initialize` is called with no reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);

    expect(() => {
      store.initialize(undefined, undefined);
    }).toThrowError('Invalid reference provided to initialize the store.');
  });

  it('calls api to fetch fleet collection when `fetchRef` is called with fleet collection reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: undefined,
      originalFleetCollection: undefined,
      originalFlow: undefined,
    });

    store.fetchRef();
    const hunt = newHunt({huntId: '123', description: 'description'});
    httpApiService.mockedObservables.fetchHunt.next(hunt);

    expect(httpApiService.fetchHunt).toHaveBeenCalledWith('123', 0);
    expect(store.originalFleetCollection()).toEqual(hunt);
  });

  it('calls api to fetch flow when `fetchRef` is called with flow reference', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: undefined,
      originalFlowRef: {clientId: 'C.123', flowId: '123'},
      originalFleetCollection: undefined,
      originalFlow: undefined,
    });

    store.fetchRef();
    const flow = newFlow({clientId: 'C.123', flowId: '123', name: 'flow'});
    httpApiService.mockedObservables.fetchFlow.next(flow);

    expect(httpApiService.fetchFlow).toHaveBeenCalledWith('C.123', '123');
    expect(store.originalFlow()).toEqual(flow);
  });

  it('calls api to create fleet collection when `createFleetCollection` is called', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: undefined,
      originalFleetCollection: newHunt({huntId: '123', flowName: 'flow'}),
      originalFlow: undefined,
    });

    store.createFleetCollection(
      'description',
      {
        clientLimit: BigInt(1),
        clientRate: 2,
        expiryTime: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        perClientCpuLimit: BigInt(8),
        perClientNetworkBytesLimit: BigInt(9),
      },
      {rules: []},
      [],
    );
    const hunt = newHunt({huntId: '456', description: 'description'});
    httpApiService.mockedObservables.createHunt.next(hunt);

    expect(httpApiService.createHunt).toHaveBeenCalledWith(
      'description',
      'flow',
      undefined,
      undefined,
      {huntId: '123'},
      {
        clientLimit: BigInt(1),
        clientRate: 2,
        expiryTime: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        perClientCpuLimit: BigInt(8),
        perClientNetworkBytesLimit: BigInt(9),
      },
      {rules: []},
      [],
    );
    expect(store.newFleetCollection()).toEqual(hunt);
  });

  it('throws error when `createFleetCollection` is called an not valid flow name is available', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: undefined,
      originalFleetCollection: newHunt({huntId: '123', flowName: undefined}),
      originalFlow: undefined,
    });

    expect(() => {
      store.createFleetCollection(
        'description',
        newSafetyLimits({}),
        {rules: []},
        [],
      );
    }).toThrowError('Flow reference does not have a flow name.');
  });

  it('returns flow args from flowRef when `flowArgs` is called', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: undefined,
      originalFlowRef: {clientId: 'C.123', flowId: '123'},
      originalFleetCollection: undefined,
      originalFlow: newFlow({
        clientId: 'C.123',
        flowId: '123',
        args: {foo: 'bar'},
      }),
    });

    expect(store.flowArgs()).toEqual({foo: 'bar'});
  });

  it('returns flow args from fleet collection when `flowArgs` is called', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: undefined,
      originalFleetCollection: newHunt({
        huntId: '123',
        flowArgs: {foo: 'bar'},
      }),
      originalFlow: undefined,
    });

    expect(store.flowArgs()).toEqual({foo: 'bar'});
  });

  it('returns flow type from flowRef when `flowType` is called', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: undefined,
      originalFlowRef: {clientId: 'C.123', flowId: '123'},
      originalFleetCollection: undefined,
      originalFlow: newFlow({
        clientId: 'C.123',
        flowId: '123',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      }),
    });

    expect(store.flowType()).toEqual(FlowType.ARTIFACT_COLLECTOR_FLOW);
  });

  it('returns flow type from fleet collection when `flowType` is called', () => {
    const store = TestBed.inject(NewFleetCollectionStore);
    patchState(unprotected(store), {
      originalFleetCollectionRef: {huntId: '123'},
      originalFlowRef: undefined,
      originalFleetCollection: newHunt({
        huntId: '123',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      }),
      originalFlow: undefined,
    });

    expect(store.flowType()).toEqual(FlowType.ARTIFACT_COLLECTOR_FLOW);
  });
});
