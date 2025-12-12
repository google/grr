import {TestBed} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {OutputPluginLogEntryType} from '../lib/models/flow';
import {newFlow, newFlowResult} from '../lib/models/model_test_util';
import {PayloadType} from '../lib/models/result';
import {FlowStore} from './flow_store';

describe('FlowStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        FlowStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
    });
  });

  it('initializes `clientId` and `flowId` when calling `initialize`', () => {
    const store = TestBed.inject(FlowStore);

    store.initialize('C.1234', 'f.ABCD');

    expect(store.clientId()).toEqual('C.1234');
    expect(store.flowId()).toEqual('f.ABCD');
  });

  it('calls api to fetch flow when calling `fetchFlow`', () => {
    const store = TestBed.inject(FlowStore);
    const flow = newFlow({
      clientId: 'C.1234',
      flowId: 'f.ABCD',
    });
    patchState(unprotected(store), {clientId: 'C.1234', flowId: 'f.ABCD'});

    store.fetchFlow();
    httpApiService.mockedObservables.pollFlow.next(flow);

    expect(httpApiService.pollFlow).toHaveBeenCalledWith('C.1234', 'f.ABCD', 0);
    expect(store.flow()).toEqual(flow);
  });

  it('calls api to fetch flow results when calling `fetchFlowResults`', () => {
    const store = TestBed.inject(FlowStore);
    const flowResults = [
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
        payload: {
          username: 'testuser',
        },
      }),
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
      }),
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.STAT_ENTRY,
      }),
    ];
    patchState(unprotected(store), {clientId: 'C.1234', flowId: 'f.ABCD'});

    store.fetchFlowResults(PayloadType.USER);
    httpApiService.mockedObservables.listResultsForFlow.next({
      totalCount: 10,
      results: flowResults,
    });

    expect(httpApiService.listResultsForFlow).toHaveBeenCalledWith(
      {
        clientId: 'C.1234',
        flowId: 'f.ABCD',
        count: 500,
        offset: 0,
        withType: PayloadType.USER,
      },
      0,
    );
    expect(store.flowResultsByPayloadType()).toEqual(
      new Map([
        [PayloadType.USER, [flowResults[0], flowResults[1]]],
        [PayloadType.STAT_ENTRY, [flowResults[2]]],
      ]),
    );
    expect(store.countLoadedResults()).toEqual(3);
    expect(store.countTotalResults()).toEqual(10);
  });

  it('calls api to fetch flow logs when calling `fetchFlowLogs`', () => {
    const store = TestBed.inject(FlowStore);
    patchState(unprotected(store), {clientId: 'C.1234', flowId: 'f.ABCD'});

    store.fetchFlowLogs();
    httpApiService.mockedObservables.fetchFlowLogs.next({
      totalCount: 2,
      items: [
        {
          timestamp: new Date(1),
          logMessage: 'log message 1',
        },
        {
          timestamp: new Date(2),
          logMessage: 'log message 2',
        },
      ],
    });

    expect(httpApiService.fetchFlowLogs).toHaveBeenCalledWith(
      'C.1234',
      'f.ABCD',
    );
    expect(store.logs()).toEqual([
      {
        timestamp: new Date(1),
        logMessage: 'log message 1',
      },
      {
        timestamp: new Date(2),
        logMessage: 'log message 2',
      },
    ]);
  });

  it('calls api to fetch output plugin logs when calling `fetchAllFlowOutputPluginLogs`', () => {
    const store = TestBed.inject(FlowStore);
    patchState(unprotected(store), {clientId: 'C.1234', flowId: 'f.ABCD'});

    store.fetchAllFlowOutputPluginLogs();

    httpApiService.mockedObservables.listAllFlowOutputPluginLogs.next({
      totalCount: 2,
      items: [
        {
          timestamp: new Date(1),
          outputPluginId: '1',
          logEntryType: OutputPluginLogEntryType.LOG,
          message: 'log message 1',
        },
        {
          timestamp: new Date(2),
          outputPluginId: '1',
          logEntryType: OutputPluginLogEntryType.ERROR,
          message: 'error message 2',
        },
      ],
    });

    expect(httpApiService.listAllFlowOutputPluginLogs).toHaveBeenCalledWith(
      'C.1234',
      'f.ABCD',
    );
    expect(store.outputPluginLogs()).toEqual([
      {
        timestamp: new Date(1),
        outputPluginId: '1',
        logEntryType: OutputPluginLogEntryType.LOG,
        message: 'log message 1',
      },
      {
        timestamp: new Date(2),
        outputPluginId: '1',
        logEntryType: OutputPluginLogEntryType.ERROR,
        message: 'error message 2',
      },
    ]);
  });
});
