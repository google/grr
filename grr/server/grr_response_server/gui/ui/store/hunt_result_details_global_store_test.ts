import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom, throwError} from 'rxjs';

import {
  ApiFlow,
  ApiFlowState,
  ApiHuntError,
  ApiHuntResult,
} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {
  HttpApiServiceMock,
  mockHttpApiService,
} from '../lib/api/http_api_service_test_util';
import {translateFlow} from '../lib/api_translation/flow';
import {getHuntResultKey} from '../lib/api_translation/hunt';
import {createDate} from '../lib/api_translation/primitive';
import {PayloadType} from '../lib/models/result';
import {initTestEnvironment} from '../testing';

import {ConfigGlobalStore} from './config_global_store';
import {
  ConfigGlobalStoreMock,
  mockConfigGlobalStore,
} from './config_global_store_test_util';
import {
  HuntResultDetailsGlobalStore,
  RESULT_BATCH_COUNT,
  stringifyAndBeautify,
} from './hunt_result_details_global_store';

initTestEnvironment();

function copyTimes<T>(element: T, times: number): T[] {
  const resultingArray: T[] = [];
  for (let i = 0; i < times; i++) {
    resultingArray.push(element);
  }
  return resultingArray;
}

describe('Hunt Result Details Global Store', () => {
  let huntResultDetailsGlobalStore: HuntResultDetailsGlobalStore;
  let httpApiService: HttpApiServiceMock;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        HuntResultDetailsGlobalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
        {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    huntResultDetailsGlobalStore = TestBed.inject(HuntResultDetailsGlobalStore);
  });

  describe('Loading a Hunt Result', () => {
    it('Tries to fetch the hunt result after receiving a Hunt Result Key', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Successful search for a hunt result details', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      const mockHuntResultDetails = {
        ...mockHuntResult,
        'payload': {
          'foo': 'bar',
        },
      };

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResultDetails,
      ]);

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify(mockHuntResultDetails.payload),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Successful recursive search for a hunt result details', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      const mockHuntResultDetails = {
        ...mockHuntResult,
        payload: {
          foo: 'bar',
        },
      };

      const differentHuntResultDetails = {
        clientId: 'C.4321', // this differs
        timestamp: '1',
        payload: {
          foo: 'bar',
        },
      };

      // We first mock a response of 50 items unrelated to the hunt result key:
      httpApiService.mockedObservables.listResultsForHunt.next(
        copyTimes(differentHuntResultDetails, RESULT_BATCH_COUNT),
      );
      // we then mock a response with the result we are looking for on it:
      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResultDetails,
      ]);

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${RESULT_BATCH_COUNT}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledTimes(2);

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify(mockHuntResultDetails.payload),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Unsuccessful search for a hunt result - API call error', async () => {
      const mockHuntResultKey = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const huntResultId = getHuntResultKey(mockHuntResultKey, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        huntResultId,
        PayloadType.USER,
      );

      httpApiService.mockedObservables.listResultsForHunt.next(
        throwError('some Http error') as unknown as ApiHuntResult[],
      );

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual('Data not found');

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResultKey.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResultKey.timestamp));
    });

    it('Unsuccessful search for a hunt result - Result not found', async () => {
      const mockHuntResultKey = {
        clientId: 'C.1234',
        payloadType: 'User',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const huntResultId = getHuntResultKey(mockHuntResultKey, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        huntResultId,
        PayloadType.USER,
      );

      const mockHuntResultDetails = {
        'clientId': 'C.4321', // this differs from C.1234
        'payload': {
          'foo': 'bar',
        },
        'payloadType': 'User',
        'timestamp': '1',
      };

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResultDetails,
      ]);

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: mockHuntResultKey.payloadType,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual('Data not found');

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResultKey.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResultKey.timestamp));
    });

    it('Does not try to load a hunt result if it is already present', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultDetails = {
        ...mockHuntResult,
        'payload': {
          'foo': 'bar',
        },
      };

      // We pass both the result key and the result details by default:
      huntResultDetailsGlobalStore.selectHuntResultOrError(
        mockHuntResultDetails,
        mockHuntId,
      );

      expect(httpApiService.listResultsForHunt).not.toHaveBeenCalled();

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify(mockHuntResultDetails.payload),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Reloads the hunt result details after receiving a new result key Id', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      const mockHuntResultDetails = {
        ...mockHuntResult,
        'payload': {
          'foo': 'bar',
        },
      };

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResultDetails,
      ]);

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.USER,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify(mockHuntResultDetails.payload),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));

      const anotherMockHuntResult = {
        clientId: 'C.4321', // this differs
        timestamp: '2',
      };

      const anotherMockHuntResultKey = getHuntResultKey(
        anotherMockHuntResult,
        mockHuntId,
      );

      huntResultDetailsGlobalStore.selectHuntResultId(
        anotherMockHuntResultKey,
        PayloadType.FILE_FINDER_RESULT,
      );

      const anotherMockHuntResultDetails = {
        ...anotherMockHuntResult,
        'payload': {
          'bar': 'foo',
        },
      };

      httpApiService.mockedObservables.listResultsForHunt.next([
        anotherMockHuntResultDetails,
      ]);

      expect(httpApiService.listResultsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
        withType: PayloadType.FILE_FINDER_RESULT,
      });

      const displayValue2 = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue2).toEqual(
        stringifyAndBeautify(anotherMockHuntResultDetails.payload),
      );

      const anotherHuntId = await firstValueFrom(
        huntResultDetailsGlobalStore.huntId$,
      );
      expect(anotherHuntId).toEqual(mockHuntId);

      const anotherClientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(anotherClientId).toEqual(anotherMockHuntResult.clientId);

      const anotherTimestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(anotherTimestamp).toEqual(
        createDate(anotherMockHuntResult.timestamp),
      );
    });
  });

  describe('Loading a Hunt Error', () => {
    it('Tries to fetch the hunt error after receiving a Hunt Result Key', fakeAsync(() => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });
    }));

    it('Successful search for a hunt error details', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      const mockHuntErrorDetails = {
        clientId: mockHuntResult.clientId,
        timestamp: mockHuntResult.timestamp,
        logMessage: 'foo',
        backtrace: 'bar',
      };

      httpApiService.mockedObservables.listErrorsForHunt.next([
        mockHuntErrorDetails,
      ]);

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify({
          logMessage: mockHuntErrorDetails.logMessage,
          backtrace: mockHuntErrorDetails.backtrace,
        }),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Successful recursive search for a hunt error details', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      const mockHuntErrorDetails = {
        clientId: mockHuntResult.clientId,
        timestamp: mockHuntResult.timestamp,
        logMessage: 'foo',
        backtrace: 'bar',
      };

      const differentHuntErrorDetails = {
        clientId: 'C.4321', // this differs
        timestamp: '2',
        logMessage: 'foo',
        backtrace: 'bar',
      };

      // We first mock a response of 50 items unrelated to the hunt result key:
      httpApiService.mockedObservables.listErrorsForHunt.next(
        copyTimes(differentHuntErrorDetails, RESULT_BATCH_COUNT),
      );
      // we then mock a response with the result we are looking for on it:
      httpApiService.mockedObservables.listErrorsForHunt.next([
        mockHuntErrorDetails,
      ]);

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${RESULT_BATCH_COUNT}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledTimes(2);

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify({
          logMessage: mockHuntErrorDetails.logMessage,
          backtrace: mockHuntErrorDetails.backtrace,
        }),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Unsuccessful search for a hunt error - API call error', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      httpApiService.mockedObservables.listErrorsForHunt.next(
        throwError('some Http error') as unknown as ApiHuntError[],
      );

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual('Data not found');

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Unsuccessful search for a hunt error - Error not found', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        payloadType: PayloadType.API_HUNT_ERROR,
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      const mockHuntErrorDetails = {
        clientId: 'C.4321', // this differs from C.1234
        timestamp: mockHuntResult.timestamp,
        logMessage: 'foo',
        backtrace: 'bar',
      };

      httpApiService.mockedObservables.listErrorsForHunt.next([
        mockHuntErrorDetails,
      ]);

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual('Data not found');

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Does not try to load a hunt error if it is already present', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';
      const mockHuntErrorDetails = {
        clientId: mockHuntResult.clientId,
        timestamp: mockHuntResult.timestamp,
        logMessage: 'foo',
        backtrace: 'bar',
      };

      // We pass both the result key and the error details by default:
      huntResultDetailsGlobalStore.selectHuntResultOrError(
        mockHuntErrorDetails,
        mockHuntId,
      );

      expect(httpApiService.listErrorsForHunt).not.toHaveBeenCalled();

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify({
          logMessage: mockHuntErrorDetails.logMessage,
          backtrace: mockHuntErrorDetails.backtrace,
        }),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));
    });

    it('Reloads the hunt error details after receiving a new result key Id', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntErrorDetails = {
        clientId: mockHuntResult.clientId,
        timestamp: mockHuntResult.timestamp,
        logMessage: 'foo',
        backtrace: 'bar',
      };

      // We pass both the result key and the error details by default:
      huntResultDetailsGlobalStore.selectHuntResultOrError(
        mockHuntErrorDetails,
        mockHuntId,
      );

      expect(httpApiService.listErrorsForHunt).not.toHaveBeenCalled();

      const displayValue = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue).toEqual(
        stringifyAndBeautify({
          logMessage: mockHuntErrorDetails.logMessage,
          backtrace: mockHuntErrorDetails.backtrace,
        }),
      );

      const huntId = await firstValueFrom(huntResultDetailsGlobalStore.huntId$);
      expect(huntId).toEqual(mockHuntId);

      const clientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(clientId).toEqual(mockHuntResult.clientId);

      const timestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(timestamp).toEqual(createDate(mockHuntResult.timestamp));

      const anotherMockHuntResult = {
        clientId: 'C.4321',
        timestamp: '2',
      };

      const anotherMockHuntResultKey = getHuntResultKey(
        anotherMockHuntResult,
        mockHuntId,
      );

      huntResultDetailsGlobalStore.selectHuntResultId(
        anotherMockHuntResultKey,
        PayloadType.API_HUNT_ERROR,
      );

      const anotherMockHuntErrorDetails = {
        clientId: anotherMockHuntResult.clientId,
        timestamp: anotherMockHuntResult.timestamp,
        logMessage: 'bar',
        backtrace: 'foo',
      };

      httpApiService.mockedObservables.listErrorsForHunt.next([
        anotherMockHuntErrorDetails,
      ]);

      expect(httpApiService.listErrorsForHunt).toHaveBeenCalledWith({
        huntId: mockHuntId,
        offset: `${0}`,
        count: `${RESULT_BATCH_COUNT}`,
      });

      const displayValue2 = await firstValueFrom(
        huntResultDetailsGlobalStore.resultOrErrorDisplay$,
      );
      expect(displayValue2).toEqual(
        stringifyAndBeautify({
          logMessage: anotherMockHuntErrorDetails.logMessage,
          backtrace: anotherMockHuntErrorDetails.backtrace,
        }),
      );

      const anotherHuntId = await firstValueFrom(
        huntResultDetailsGlobalStore.huntId$,
      );
      expect(anotherHuntId).toEqual(mockHuntId);

      const anotherClientId = await firstValueFrom(
        huntResultDetailsGlobalStore.clientId$,
      );
      expect(anotherClientId).toEqual(anotherMockHuntResult.clientId);

      const anotherTimestamp = await firstValueFrom(
        huntResultDetailsGlobalStore.timestamp$,
      );
      expect(anotherTimestamp).toEqual(
        createDate(anotherMockHuntResult.timestamp),
      );
    });
  });

  describe('Flow Details', () => {
    it('Loads the flow of a Hunt Result, with its descriptor', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockFlow = {
        flowId: mockHuntId,
        clientId: mockHuntResult.clientId,
        lastActiveAt: '2',
        startedAt: '1',
        name: 'User',
        creator: '',
        args: undefined,
        progress: undefined,
        state: ApiFlowState.RUNNING,
        errorDescription: undefined,
        isRobot: false,
      };

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      const mockDescriptor = {
        name: PayloadType.USER,
        friendlyName: 'User',
        category: 'User',
        blockHuntCreation: false,
        defaultArgs: undefined,
      };

      const mockDescriptorsMap = new Map([[PayloadType.USER, mockDescriptor]]);

      configGlobalStore.mockedObservables.flowDescriptors$.next(
        mockDescriptorsMap,
      );
      httpApiService.mockedObservables.fetchFlow.next(mockFlow);

      expect(httpApiService.fetchFlow).toHaveBeenCalledWith(
        mockHuntResult.clientId,
        mockHuntId,
      );

      const flowWithDescriptor = await firstValueFrom(
        huntResultDetailsGlobalStore.flowWithDescriptor$,
      );

      expect(flowWithDescriptor).toEqual({
        flow: translateFlow(mockFlow),
        descriptor: mockDescriptor,
        flowArgType: undefined,
      });
    });

    it('Does not re-fetch the flow if it is already present', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      expect(httpApiService.fetchFlow).toHaveBeenCalledWith(
        mockHuntResult.clientId,
        mockHuntId,
      );

      huntResultDetailsGlobalStore.selectHuntResultId(mockHuntResultKey);

      expect(httpApiService.fetchFlow).toHaveBeenCalledTimes(1);
    });

    it('Re-fetches the flow after receiving a new result key Id', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      expect(httpApiService.fetchFlow).toHaveBeenCalledWith(
        mockHuntResult.clientId,
        mockHuntId,
      );

      const anotherMockHuntResult = {
        clientId: 'C.4321', // This differs
        timestamp: '1',
      };
      const anotherMockHuntResultKey = getHuntResultKey(
        anotherMockHuntResult,
        mockHuntId,
      );

      huntResultDetailsGlobalStore.selectHuntResultId(anotherMockHuntResultKey);

      expect(httpApiService.fetchFlow).toHaveBeenCalledWith(
        anotherMockHuntResult.clientId,
        mockHuntId,
      );

      expect(httpApiService.fetchFlow).toHaveBeenCalledTimes(2);
    });

    it('Does not find the flow and returns undefined', async () => {
      const mockHuntResult = {
        clientId: 'C.1234',
        timestamp: '1',
      };
      const mockHuntId = 'ABCD1234';

      const mockHuntResultKey = getHuntResultKey(mockHuntResult, mockHuntId);

      huntResultDetailsGlobalStore.selectHuntResultId(
        mockHuntResultKey,
        PayloadType.USER,
      );

      // No descriptors:
      configGlobalStore.mockedObservables.flowDescriptors$.next(new Map());
      httpApiService.mockedObservables.fetchFlow.next(
        undefined as unknown as ApiFlow,
      );

      expect(httpApiService.fetchFlow).toHaveBeenCalledWith(
        mockHuntResult.clientId,
        mockHuntId,
      );

      const flowWithDescriptor = await firstValueFrom(
        huntResultDetailsGlobalStore.flowWithDescriptor$,
      );

      expect(flowWithDescriptor).toEqual(undefined);
    });
  });
});
