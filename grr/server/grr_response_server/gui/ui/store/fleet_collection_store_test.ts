import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {DEFAULT_POLLING_INTERVAL} from '../lib/api/http_api_service';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {HuntState, ListHuntErrorsResult} from '../lib/models/hunt';
import {
  newHunt,
  newHuntApproval,
  newHuntError,
  newHuntResult,
  newSafetyLimits,
} from '../lib/models/model_test_util';
import {PayloadType} from '../lib/models/result';
import {FleetCollectionStore} from './fleet_collection_store';

describe('Fleet Collection Store', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        FleetCollectionStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
    });
  });

  it('`initialize` initializes the store with the correct initial state', () => {
    const store = TestBed.inject(FleetCollectionStore);

    store.initialize('ABCD1234');

    expect(store.fleetCollectionId()).toBe('ABCD1234');
    expect(store.fleetCollection()).toBeNull();
    expect(store.hasAccess()).toBeFalse();
    expect(store.fleetCollectionApprovals()).toEqual([]);
    expect(store.fleetCollectionResults()).toEqual([]);
    expect(store.totalResultsCount()).toEqual(0);
    expect(store.fleetCollectionErrors()).toEqual([]);
    expect(store.totalErrorsCount()).toEqual(0);
    expect(store.fleetCollectionProgress()).toBeNull();
    expect(store.fleetCollectionLogs()).toEqual([]);
    expect(store.totalFleetCollectionLogsCount()).toEqual(0);
  });

  it('calls api to verify hunt access and updates store when `pollUntilAccess` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollUntilAccess('ABCD1234');
    tick();
    httpApiService.mockedObservables.verifyHuntAccess.next(true);

    expect(store.hasAccess()).toBeTrue();
  }));

  it('calls api to fetch fleet collection approvals and updates store when `pollFleetCollectionApprovals` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);
    const approvals = [newHuntApproval({}), newHuntApproval({})];

    store.pollFleetCollectionApprovals('ABCD1234');
    tick();
    httpApiService.mockedObservables.listHuntApprovals.next(approvals);

    expect(httpApiService.listHuntApprovals).toHaveBeenCalledWith(
      'ABCD1234',
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.fleetCollectionApprovals()).toEqual(approvals);
  }));

  it('returns null for latestApproval if there are no approvals', () => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollectionApprovals('ABCD1234');
    httpApiService.mockedObservables.listHuntApprovals.next([]);

    expect(store.latestApproval()).toBeNull();
  });

  it('returns null for latestApproval if there are only expired approvals', () => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollectionApprovals('ABCD1234');
    const expiredApproval = newHuntApproval({
      huntId: 'ABCD1234',
      status: {type: 'expired', reason: 'Expired'},
    });
    httpApiService.mockedObservables.listHuntApprovals.next([expiredApproval]);
    expect(store.latestApproval()).toBeNull();
  });

  it('returns the latest not expired approval for latestApproval', () => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollectionApprovals('ABCD1234');
    const pendingApproval = newHuntApproval({
      huntId: 'ABCD1234',
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    const expiredApproval = newHuntApproval({
      huntId: 'ABCD1234',
      status: {type: 'expired', reason: 'Expired'},
    });

    httpApiService.mockedObservables.listHuntApprovals.next([
      expiredApproval,
      pendingApproval,
    ]);

    expect(store.latestApproval()).toEqual(pendingApproval);
  });

  it('calls api to fetch fleet collection and updates store when `pollFleetCollection` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollection('ABCD1234');
    tick();
    const fleetCollection = newHunt({huntId: 'ABCD1234'});
    httpApiService.mockedObservables.fetchHunt.next(fleetCollection);

    expect(httpApiService.fetchHunt).toHaveBeenCalledWith(
      'ABCD1234',
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.fleetCollection()).toEqual(fleetCollection);
  }));

  it('calls api to fetch fleet collection results and updates store when `pollFleetCollectionResults` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollectionResults({
      huntId: 'ABCD1234',
      count: 100,
      offset: 0,
    });
    tick();
    const listHuntResults = {
      results: [newHuntResult({}), newHuntResult({})],
      totalCount: 2,
    };
    httpApiService.mockedObservables.listResultsForHunt.next(listHuntResults);

    expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
      count: 100,
      huntId: 'ABCD1234',
      offset: 0,
    });
    expect(store.fleetCollectionResults()).toEqual(listHuntResults.results);
    expect(store.totalResultsCount()).toEqual(listHuntResults.totalCount);
  }));

  it('returns false for `hasMoreResults` when there are no more results than the store holds', () => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionResults: [newHuntResult({}), newHuntResult({})],
    });
    patchState(unprotected(store), {totalResultsCount: 2});

    expect(store.hasMoreResults()).toBeFalse();
  });

  it('returns true for `hasMoreResults` when there are more results than the store holds', () => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionResults: [newHuntResult({}), newHuntResult({})],
    });
    patchState(unprotected(store), {totalResultsCount: 3});

    expect(store.hasMoreResults()).toBeTrue();
  });

  it('returns a list of results per client and type for `fleetCollectionResultsPerClientAndType`', () => {
    const store = TestBed.inject(FleetCollectionStore);
    const huntResult1 = newHuntResult({
      clientId: 'C.1234',
      payloadType: PayloadType.USER,
    });
    const huntResult2 = newHuntResult({
      clientId: 'C.1234',
      payloadType: PayloadType.STAT_ENTRY,
    });
    const huntResult3 = newHuntResult({
      clientId: 'C.1234',
      payloadType: PayloadType.STAT_ENTRY,
    });
    const huntResult4 = newHuntResult({
      clientId: 'C.5678',
      payloadType: PayloadType.STAT_ENTRY,
    });
    patchState(unprotected(store), {
      fleetCollectionResults: [
        huntResult1,
        huntResult2,
        huntResult3,
        huntResult4,
      ],
    });
    expect(store.fleetCollectionResultsPerClientAndType()).toEqual([
      {
        clientId: 'C.1234',
        resultType: PayloadType.USER,
        results: [huntResult1],
      },
      {
        clientId: 'C.1234',
        resultType: PayloadType.STAT_ENTRY,
        results: [huntResult2, huntResult3],
      },
      {
        clientId: 'C.5678',
        resultType: PayloadType.STAT_ENTRY,
        results: [huntResult4],
      },
    ]);
  });
  it('calls api to fetch fleet collection errors and updates store when `getFleetCollectionErrors` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.getFleetCollectionErrors({
      huntId: 'ABCD1234',
      count: 100,
      offset: 0,
    });
    tick();
    const listHuntErrors: ListHuntErrorsResult = {
      totalCount: 2,
      errors: [
        {
          clientId: 'C.1234',
          logMessage: 'fooLog',
          backtrace: 'fooTrace',
          timestamp: new Date(1677685676900226),
        },
        {
          clientId: 'C.5678',
          logMessage: 'barLog',
          backtrace: 'barTrace',
          timestamp: new Date(1677685676900227),
        },
      ],
    };
    httpApiService.mockedObservables.listErrorsForHunt.next(listHuntErrors);

    expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
      count: 100,
      huntId: 'ABCD1234',
      offset: 0,
    });
    expect(store.fleetCollectionErrors()).toEqual(listHuntErrors.errors);
    expect(store.totalErrorsCount()).toEqual(listHuntErrors.totalCount!);
  }));

  it('calls api to fetch fleet collection progress and updates store when `pollFleetCollectionProgress` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.pollFleetCollectionProgress('ABCD1234');
    tick();
    const getHuntClientCompletionStatsResult = {
      startPoints: [
        {xValue: 1669026900000, yValue: 0},
        {xValue: 1669026900000, yValue: 0},
        {xValue: 1669026900000, yValue: 0},
      ],
      completePoints: [
        {xValue: 1669026900000, yValue: 0},
        {xValue: 1669026900000, yValue: 7},
        {xValue: 1669026900000, yValue: 29},
      ],
    };
    httpApiService.mockedObservables.getHuntClientCompletionStats.next(
      getHuntClientCompletionStatsResult,
    );

    expect(httpApiService.getHuntClientCompletionStats).toHaveBeenCalledWith(
      {
        huntId: 'ABCD1234',
        size: '100',
      },
      DEFAULT_POLLING_INTERVAL,
    );
    expect(store.fleetCollectionProgress()).toEqual(
      getHuntClientCompletionStatsResult,
    );
  }));

  it('returns false for `hasMoreErrors` when there are no more errors than the store holds', () => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionErrors: [newHuntError({}), newHuntError({})],
    });
    patchState(unprotected(store), {totalErrorsCount: 2});

    expect(store.hasMoreErrors()).toBeFalse();
  });

  it('returns true for `hasMoreErrors` when there are more errors than the store holds', () => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionErrors: [newHuntError({}), newHuntError({})],
    });
    patchState(unprotected(store), {totalErrorsCount: 3});

    expect(store.hasMoreErrors()).toBeTrue();
  });

  it('calls api to request fleet collection approval when `requestFleetCollectionApproval` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.requestFleetCollectionApproval(
      'ABCD1234',
      'reason',
      ['approver1', 'approver2'],
      ['cc1@example.com', 'cc2@example.com'],
    );
    httpApiService.mockedObservables.requestHuntApproval.next(
      newHuntApproval({
        huntId: 'ABCD1234',
        status: {type: 'pending', reason: 'Need 2 more approver'},
      }),
    );

    expect(httpApiService.requestHuntApproval).toHaveBeenCalledWith({
      huntId: 'ABCD1234',
      reason: 'reason',
      approvers: ['approver1', 'approver2'],
      cc: ['cc1@example.com', 'cc2@example.com'],
    });
  }));

  it('calls api to fetch fleet collection approvals after requesting approval', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.requestFleetCollectionApproval(
      'ABCD1234',
      'reason',
      ['approver1', 'approver2'],
      ['cc1@example.com', 'cc2@example.com'],
    );
    httpApiService.mockedObservables.requestHuntApproval.next(
      newHuntApproval({
        huntId: 'ABCD1234',
        status: {type: 'pending', reason: 'Need 2 more approver'},
      }),
    );
    httpApiService.mockedObservables.listHuntApprovals.next([
      newHuntApproval({
        huntId: 'ABCD1234',
        status: {type: 'pending', reason: 'Need 2 more approver'},
      }),
    ]);

    expect(httpApiService.listHuntApprovals).toHaveBeenCalledWith(
      'ABCD1234',
      0,
    );
  }));

  it('calls api to start fleet collection when `startFleetCollection` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionId: 'ABCD1234',
    });

    store.startFleetCollection();
    const updatedFleetCollection = newHunt({
      huntId: 'ABCD1234',
      state: HuntState.RUNNING,
    });
    httpApiService.mockedObservables.patchHunt.next(updatedFleetCollection);
    expect(httpApiService.patchHunt).toHaveBeenCalledWith('ABCD1234', {
      state: HuntState.RUNNING,
    });
    expect(store.fleetCollection()).toEqual(updatedFleetCollection);
  }));

  it('calls api to cancel fleet collection when `cancelFleetCollection` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionId: 'ABCD1234',
    });

    store.cancelFleetCollection();
    const updatedFleetCollection = newHunt({
      huntId: 'ABCD1234',
      state: HuntState.CANCELLED,
    });
    httpApiService.mockedObservables.patchHunt.next(updatedFleetCollection);
    expect(httpApiService.patchHunt).toHaveBeenCalledWith('ABCD1234', {
      state: HuntState.CANCELLED,
    });
    expect(store.fleetCollection()).toEqual(updatedFleetCollection);
  }));

  it('calls api to update fleet collection when `updateFleetCollection` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);
    patchState(unprotected(store), {
      fleetCollectionId: 'ABCD1234',
    });

    store.updateFleetCollection(BigInt(100), 10);
    const updatedFleetCollection = newHunt({
      huntId: 'ABCD1234',
      safetyLimits: newSafetyLimits({
        clientLimit: BigInt(100),
        clientRate: 10,
      }),
    });
    httpApiService.mockedObservables.patchHunt.next(updatedFleetCollection);
    expect(httpApiService.patchHunt).toHaveBeenCalledWith('ABCD1234', {
      clientLimit: BigInt(100),
      clientRate: 10,
    });
    expect(store.fleetCollection()).toEqual(updatedFleetCollection);
  }));

  it('calls api to fetch fleet collection logs and updates store when `fetchFleetCollectionLogs` is called', fakeAsync(() => {
    const store = TestBed.inject(FleetCollectionStore);

    store.fetchFleetCollectionLogs('ABCD1234');
    tick();
    httpApiService.mockedObservables.fetchHuntLogs.next({
      logs: [
        {
          timestamp: new Date(1571789996681),
          clientId: 'C.1234567890',
          flowId: 'F1234567890',
          logMessage: 'log message',
        },
      ],
      totalCount: 1,
    });

    expect(httpApiService.fetchHuntLogs).toHaveBeenCalledWith('ABCD1234');
    expect(store.fleetCollectionLogs()).toEqual([
      {
        timestamp: new Date(1571789996681),
        clientId: 'C.1234567890',
        flowId: 'F1234567890',
        logMessage: 'log message',
      },
    ]);
    expect(store.totalFleetCollectionLogsCount()).toEqual(1);
  }));
});
