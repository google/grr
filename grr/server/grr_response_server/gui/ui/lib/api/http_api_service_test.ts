import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {lastValueFrom} from 'rxjs';

import {initTestEnvironment} from '../../testing';
import {newSafetyLimits} from '../models/model_test_util';
import {OutputPluginType} from '../models/output_plugin';
import {
  ApiBrowseFilesystemResult,
  ApiCountHuntResultsByTypeResult,
  ApiFlowResult,
  ApiGetFileDetailsResult,
  ApiGetHuntClientCompletionStatsResult,
  ApiGetVfsFileContentUpdateStateResult,
  ApiGetVfsFileContentUpdateStateResultState,
  ApiGetVfsRefreshOperationStateResult,
  ApiGetVfsRefreshOperationStateResultState,
  ApiListFlowDescriptorsResult,
  ApiListFlowResultsResult,
  ApiListHuntResultsResult,
  ApiListOutputPluginDescriptorsResult,
  ApiUpdateVfsFileContentResult,
  PathSpecPathType,
} from './api_interfaces';
import {
  DEFAULT_POLLING_INTERVAL,
  HttpApiService,
  URL_PREFIX,
} from './http_api_service';
import {ApiModule} from './module';

initTestEnvironment();

describe('HttpApiService', () => {
  let httpApiService: HttpApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ApiModule, HttpClientTestingModule],
      teardown: {destroyAfterEach: false},
    });

    httpApiService = TestBed.inject(HttpApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('updateVfsFileContent posts, then polls, then gets VFS data', fakeAsync(async () => {
    const observable = httpApiService.updateVfsFileContent({
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
    });

    // Create Promise to register a subscription, which activates the
    // Observable computation.
    const valuePromise = lastValueFrom(observable);

    // First, check that the recollection is triggered.
    const req1 = httpMock.expectOne({
      method: 'POST',
      url: `${URL_PREFIX}/clients/C.1234/vfs-update`,
    });
    expect(req1.request.body.filePath).toBe('/fs/os/foo/bar');
    const resp1: ApiUpdateVfsFileContentResult = {operationId: 'op123'};
    req1.flush(resp1);

    // Then, check that the recollection status is polled, but indicate it is
    // still running.
    tick();
    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-update/op123`,
    });
    const resp2: ApiGetVfsFileContentUpdateStateResult = {
      state: ApiGetVfsFileContentUpdateStateResultState.RUNNING,
    };
    req2.flush(resp2);

    // Then, check that the recollection polls again, now indicating it has
    // been completed.
    tick(DEFAULT_POLLING_INTERVAL);
    // Validate that the reloading of the details is not started while
    // vfs-update still reports FINISHED.
    httpMock.expectNone(
      `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`,
    );
    const req3 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-update/op123`,
    });
    const resp3: ApiGetVfsFileContentUpdateStateResult = {
      state: ApiGetVfsFileContentUpdateStateResultState.FINISHED,
    };
    req3.flush(resp3);

    // Finally, check that the new file metadata is loaded and returned.
    const req4 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`,
    });
    const resp4: ApiGetFileDetailsResult = {file: {name: 'BAR'}};
    req4.flush(resp4);

    expect(await valuePromise).toEqual({file: {name: 'BAR'}});
  }));

  it('refreshVfsFolder posts, then polls, then gets VFS data', fakeAsync(async () => {
    const observable = httpApiService.refreshVfsFolder({
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/C:/bar',
    });

    // Create Promise to register a subscription, which activates the
    // Observable computation.
    const valuePromise = lastValueFrom(observable);

    // First, check that the recollection is triggered.
    const req1 = httpMock.expectOne({
      method: 'POST',
      url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations`,
    });
    expect(req1.request.body.filePath).toBe('/fs/os/C:/bar');
    const resp1: ApiUpdateVfsFileContentResult = {operationId: 'op123'};
    req1.flush(resp1);

    // Then, check that the recollection status is polled, but indicate it is
    // still running.
    tick();
    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations/op123`,
    });
    const resp2: ApiGetVfsRefreshOperationStateResult = {
      state: ApiGetVfsRefreshOperationStateResultState.RUNNING,
    };
    req2.flush(resp2);

    // Then, check that the recollection polls again, now indicating it has
    // been completed.
    tick(DEFAULT_POLLING_INTERVAL);
    // Validate that the reloading of the details is not started while
    // vfs-refresh-operations still reports FINISHED.
    httpMock.expectNone(
      `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/C%3A/bar?include_directory_tree=false`,
    );
    const req3 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations/op123`,
    });
    const resp3: ApiGetVfsRefreshOperationStateResult = {
      state: ApiGetVfsRefreshOperationStateResultState.FINISHED,
    };
    req3.flush(resp3);

    // Finally, check that the new file metadata is loaded and returned.
    const req4 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/filesystem/C%3A/bar?include_directory_tree=false`,
    });
    const resp4: ApiBrowseFilesystemResult = {
      rootEntry: {
        file: {name: 'BAR', isDirectory: false, path: 'fs/os/bar'},
        children: [],
      },
    };
    req4.flush(resp4);

    expect(await valuePromise).toEqual(resp4);
  }));

  describe('startFlow', () => {
    it('sends a POST request to the correct endpoint', fakeAsync(() => {
      const request = httpApiService
        .startFlow(
          'C.1234',
          'FileFinder',
          {
            'foo': 'bar',
          },
          true,
        )
        .subscribe();

      const descriptorReq = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/flows/descriptors`,
      });

      const descriptorResp: ApiListFlowDescriptorsResult = {
        items: [
          {
            name: 'FileFinder',
            friendlyName: 'Client Side File Finder',
            category: 'b',
            defaultArgs: {
              '@type': 'type.googleapis.com/foo.bar.FileFinderArgs',
            },
          },
        ],
      };
      descriptorReq.flush(descriptorResp);
      tick();

      const huntReq = httpMock.expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/clients/C.1234/flows`,
      });
      expect(huntReq.request.body.clientId).toBe('C.1234');
      expect(huntReq.request.body.flow.name).toBe('FileFinder');
      expect(huntReq.request.body.flow.args).toEqual({
        '@type': 'type.googleapis.com/foo.bar.FileFinderArgs',
        'foo': 'bar',
      });
      expect(huntReq.request.body.flow.runnerArgs).toEqual({
        'disableRrgSupport': true,
      });

      request.unsubscribe();
    }));
  });

  it('listResultsForFlow polls if requested', fakeAsync(() => {
    const values: Array<readonly ApiFlowResult[]> = [];
    const sub = httpApiService
      .listResultsForFlow(
        {
          clientId: 'C.1234',
          flowId: '5678',
          count: 10,
        },
        DEFAULT_POLLING_INTERVAL,
      )
      .subscribe((result) => {
        values.push(result.items ?? []);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
    });
    const resp1: ApiListFlowResultsResult = {items: [{tag: 'foo'}]};
    req1.flush(resp1);

    expect(values.length).toEqual(1);
    expect(values).toEqual([[{tag: 'foo'}]]);

    tick(DEFAULT_POLLING_INTERVAL);

    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
    });
    const resp2: ApiListFlowResultsResult = {items: [{tag: 'bar'}]};
    req2.flush(resp2);

    expect(values.length).toEqual(2);
    expect(values[1]).toEqual([{tag: 'bar'}]);

    sub.unsubscribe();

    tick(DEFAULT_POLLING_INTERVAL * 2);
    // afterEach() verifies that no further request was launched.
  }));

  it('listResultsForFlow waits for result before re-polling', fakeAsync(() => {
    const values: Array<readonly ApiFlowResult[]> = [];
    const sub = httpApiService
      .listResultsForFlow(
        {
          clientId: 'C.1234',
          flowId: '5678',
          count: 10,
        },
        DEFAULT_POLLING_INTERVAL,
      )
      .subscribe((result) => {
        values.push(result.items ?? []);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
    });

    tick(DEFAULT_POLLING_INTERVAL * 2);

    httpMock.verify();

    const resp1: ApiListFlowResultsResult = {items: [{tag: 'foo'}]};
    req1.flush(resp1);
    expect(values.length).toEqual(1);
    expect(values).toEqual([[{tag: 'foo'}]]);

    sub.unsubscribe();
  }));

  it('listResultsForHunt polls if requested', fakeAsync(() => {
    const values: ApiListHuntResultsResult[] = [];
    const sub = httpApiService
      .listResultsForHunt(
        {huntId: '1234', count: '10'},
        DEFAULT_POLLING_INTERVAL,
      )
      .subscribe((result) => {
        values.push(result);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });
    const resp1: ApiListHuntResultsResult = {
      totalCount: '1',
      items: [{clientId: 'C.1'}],
    };
    req1.flush(resp1);

    expect(values.length).toEqual(1);
    expect(values).toEqual([{totalCount: '1', items: [{clientId: 'C.1'}]}]);

    tick(DEFAULT_POLLING_INTERVAL);

    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });
    const resp2: ApiListHuntResultsResult = {
      totalCount: '2',
      items: [{clientId: 'C.2'}],
    };
    req2.flush(resp2);

    expect(values.length).toEqual(2);
    expect(values[1]).toEqual({totalCount: '2', items: [{clientId: 'C.2'}]});

    sub.unsubscribe();

    tick(DEFAULT_POLLING_INTERVAL * 2);
    // afterEach() verifies that no further request was launched.
  }));

  it('listResultsForHunt waits for result before re-polling', fakeAsync(() => {
    const values: ApiListHuntResultsResult[] = [];
    const sub = httpApiService
      .listResultsForHunt(
        {huntId: '1234', count: '10'},
        DEFAULT_POLLING_INTERVAL,
      )
      .subscribe((result) => {
        values.push(result);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });

    tick(DEFAULT_POLLING_INTERVAL * 2);

    httpMock.verify();

    const resp1: ApiListHuntResultsResult = {
      items: [{clientId: 'C.1'}],
    };
    req1.flush(resp1);
    expect(values.length).toEqual(1);
    expect(values).toEqual([{items: [{clientId: 'C.1'}]}]);

    sub.unsubscribe();
  }));

  it('getFileAccess calls the correct endpoint', fakeAsync(() => {
    httpApiService
      .getFileAccess({
        clientId: 'C.1234',
        pathType: PathSpecPathType.OS,
        path: '/foo/bar',
      })
      .subscribe();

    const req = httpMock.expectOne({
      method: 'HEAD',
      url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`,
    });
    expect(req).toBeTruthy();
    req.flush({});
  }));

  it('getFileDetails handles Windows paths correctly', fakeAsync(() => {
    httpApiService
      .getFileDetails({
        clientId: 'C.1234',
        pathType: PathSpecPathType.TSK,
        path: 'C:/Windows/foo',
      })
      .subscribe();

    const req = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/tsk/C%3A/Windows/foo`,
    });

    // Dummy assertion to prevent warnings about missing assertions.
    expect(req).toBeTruthy();
    req.flush({});
  }));

  it('getFileDetails handles root', fakeAsync(() => {
    httpApiService
      .getFileDetails({
        clientId: 'C.1234',
        pathType: PathSpecPathType.OS,
        path: '/',
      })
      .subscribe();

    const req = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/`,
    });

    // Dummy assertion to prevent warnings about missing assertions.
    expect(req).toBeTruthy();
    req.flush({});
  }));

  it('getFileDetails handles unix paths correctly root', fakeAsync(() => {
    httpApiService
      .getFileDetails({
        clientId: 'C.1234',
        pathType: PathSpecPathType.OS,
        path: '/foo/bar',
      })
      .subscribe();

    const req = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`,
    });

    // Dummy assertion to prevent warnings about missing assertions.
    expect(req).toBeTruthy();
    req.flush({});
  }));

  it('fetchWebAuthType calls the correct endpoint', fakeAsync(() => {
    httpApiService.fetchWebAuthType().subscribe();

    const req = httpMock.expectOne({
      method: 'GET',
      url: '/api/v2/config/AdminUI.webauth_manager',
    });

    // Dummy assertion to prevent warnings about missing assertions.
    expect(req).toBeTruthy();
    req.flush({});
  }));

  it('fetchExportCommandPrefix calls the correct endpoint', fakeAsync(() => {
    httpApiService.fetchExportCommandPrefix().subscribe();

    const req = httpMock.expectOne({
      method: 'GET',
      url: '/api/v2/config/AdminUI.export_command',
    });

    // Dummy assertion to prevent warnings about missing assertions.
    expect(req).toBeTruthy();
    req.flush({});
  }));

  describe('createHunt', () => {
    it('sends a POST request to the correct endpoint', fakeAsync(() => {
      const request = httpApiService
        .createHunt(
          'description',
          'FileFinder',
          {
            'foo': 'bar',
          },
          {clientId: 'C.1234', flowId: '5678'},
          undefined,
          newSafetyLimits({
            clientRate: 111,
            clientLimit: BigInt(222),
            crashLimit: BigInt(333),
            expiryTime: BigInt(444),
            avgResultsPerClientLimit: BigInt(555),
            avgCpuSecondsPerClientLimit: BigInt(666),
            avgNetworkBytesPerClientLimit: BigInt(777),
            perClientCpuLimit: BigInt(888),
            perClientNetworkBytesLimit: BigInt(999),
          }),
          {rules: []},
          [
            {
              pluginType: OutputPluginType.EMAIL,
              args: {
                emailAddress: 'test@example.com',
              },
            },
          ],
        )
        .subscribe();

      const descriptorReq = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/flows/descriptors`,
      });

      const descriptorResp: ApiListFlowDescriptorsResult = {
        items: [
          {
            name: 'FileFinder',
            friendlyName: 'Client Side File Finder',
            category: 'b',
            defaultArgs: {
              '@type': 'type.googleapis.com/foo.bar.FileFinderArgs',
            },
          },
        ],
      };
      descriptorReq.flush(descriptorResp);
      tick();

      const outputPluginReq = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/output-plugins/all`,
      });

      const outputPluginResp: ApiListOutputPluginDescriptorsResult = {
        items: [
          {
            name: 'EmailOutputPlugin',
            friendlyName: 'Email Output Plugin',
            description: 'Email output plugin description',
            argsType: 'type.googleapis.com/foo.bar.EmailOutputPluginArgs',
          },
        ],
      };
      outputPluginReq.flush(outputPluginResp);
      tick();

      const huntReq = httpMock.expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/hunts`,
      });
      expect(huntReq.request.body.flowName).toBe('FileFinder');
      expect(huntReq.request.body.flowArgs).toEqual({
        '@type': 'type.googleapis.com/foo.bar.FileFinderArgs',
        'foo': 'bar',
      });
      expect(huntReq.request.body.originalFlow).toEqual({
        clientId: 'C.1234',
        flowId: '5678',
      });
      expect(huntReq.request.body.originalHunt).toBeUndefined();
      expect(huntReq.request.body.huntRunnerArgs).toEqual({
        description: 'description',
        clientRate: 111,
        clientLimit: '222',
        crashLimit: '333',
        expiryTime: '444',
        avgResultsPerClientLimit: '555',
        avgCpuSecondsPerClientLimit: '666',
        avgNetworkBytesPerClientLimit: '777',
        perClientCpuLimit: '888',
        perClientNetworkLimitBytes: '999',
        clientRuleSet: {rules: []},
        outputPlugins: [
          {
            pluginName: 'EmailOutputPlugin',
            args: {
              '@type': 'type.googleapis.com/foo.bar.EmailOutputPluginArgs',
              emailAddress: 'test@example.com',
            },
          },
        ],
      });

      request.unsubscribe();
    }));
  });

  describe('getHuntClientCompletionStats', () => {
    it(`Doesn't send a "size" HTTPParam if not specified`, fakeAsync(() => {
      const sub = httpApiService
        .getHuntClientCompletionStats({huntId: '1234', size: undefined})
        .subscribe();

      tick();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/1234/client-completion-stats`,
      });

      sub.unsubscribe();
    }));

    it('polls getHuntClientCompletionStats', fakeAsync(() => {
      const values: ApiGetHuntClientCompletionStatsResult[] = [];
      const sub = httpApiService
        .getHuntClientCompletionStats(
          {huntId: '1234', size: '10'},
          DEFAULT_POLLING_INTERVAL,
        )
        .subscribe((result) => {
          values.push(result);
        });

      tick();

      const req1 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/1234/client-completion-stats?size=10`,
      });

      const resp1: ApiGetHuntClientCompletionStatsResult = {
        completePoints: [{xValue: 1678380000, yValue: 1}],
        startPoints: [{xValue: 1678380000, yValue: 1}],
      };

      req1.flush(resp1);

      expect(values.length).toEqual(1);
      expect(values).toEqual([resp1]);

      tick(DEFAULT_POLLING_INTERVAL);

      const req2 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/1234/client-completion-stats?size=10`,
      });

      const resp2: ApiGetHuntClientCompletionStatsResult = {
        completePoints: [{xValue: 1678380001, yValue: 1}],
        startPoints: [{xValue: 1678380001, yValue: 1}],
      };

      req2.flush(resp2);

      expect(values.length).toEqual(2);
      expect(values[1]).toEqual(resp2);

      sub.unsubscribe();

      tick(DEFAULT_POLLING_INTERVAL * 2);
      // afterEach() verifies that no further request was launched.
    }));

    it('Waits for result before re-polling', fakeAsync(() => {
      const values: ApiGetHuntClientCompletionStatsResult[] = [];
      const sub = httpApiService
        .getHuntClientCompletionStats(
          {huntId: '1234', size: '10'},
          DEFAULT_POLLING_INTERVAL,
        )
        .subscribe((result) => {
          values.push(result);
        });

      tick();

      const req1 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/1234/client-completion-stats?size=10`,
      });

      tick(DEFAULT_POLLING_INTERVAL * 2);

      httpMock.verify();

      const resp1: ApiGetHuntClientCompletionStatsResult = {
        completePoints: [{xValue: 1678380000, yValue: 1}],
        startPoints: [{xValue: 1678380000, yValue: 1}],
      };

      req1.flush(resp1);
      expect(values.length).toEqual(1);
      expect(values).toEqual([resp1]);

      sub.unsubscribe();
    }));
  });

  describe('getHuntResultsByType', () => {
    it('polls if requestț', fakeAsync(() => {
      const huntId = '1234';
      let resultsByType: ApiCountHuntResultsByTypeResult = {};
      const sub = httpApiService
        .getHuntResultsByType(huntId, DEFAULT_POLLING_INTERVAL)
        .subscribe((result) => {
          resultsByType = result;
        });

      tick();

      const req1 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/result-counts`,
      });

      const resp1: ApiCountHuntResultsByTypeResult = {
        items: [
          {
            type: 'FileFinderResult',
            count: '10',
          },
        ],
      };

      req1.flush(resp1);

      expect(resultsByType?.items?.length).toEqual(1);
      expect(resultsByType).toEqual(resp1);

      tick(DEFAULT_POLLING_INTERVAL);

      const req2 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/result-counts`,
      });

      const resp2: ApiCountHuntResultsByTypeResult = {
        items: [
          {
            type: 'FileFinderResult',
            count: '20',
          },
          {
            type: 'User',
            count: '5',
          },
        ],
      };

      req2.flush(resp2);

      expect(resultsByType?.items?.length).toEqual(2);
      expect(resultsByType).toEqual(resp2);

      sub.unsubscribe();

      tick(DEFAULT_POLLING_INTERVAL * 2);
      // afterEach() verifies that no further request was launched.
    }));

    it('Waits for result before re-polling', fakeAsync(() => {
      const huntId = '1234';
      let resultsByType: ApiCountHuntResultsByTypeResult = {};
      const sub = httpApiService
        .getHuntResultsByType(huntId, DEFAULT_POLLING_INTERVAL)
        .subscribe((result) => {
          resultsByType = result;
        });

      tick(DEFAULT_POLLING_INTERVAL * 2);

      const req1 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/result-counts`,
      });

      const resp1: ApiCountHuntResultsByTypeResult = {
        items: [
          {
            type: 'FileFinderResult',
            count: '10',
          },
        ],
      };

      req1.flush(resp1);

      expect(resultsByType?.items?.length).toEqual(1);
      expect(resultsByType).toEqual(resp1);

      sub.unsubscribe();
    }));
  });

  describe('listResultsForHunt', () => {
    it("calls http service's GET with the huntId", () => {
      const huntId = '1234';

      httpApiService.listResultsForHunt({huntId}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        // Note: camelCase works due to the following being a GET request. It
        // wouldn't work on a POST one due to TODO
        url: `${URL_PREFIX}/hunts/${huntId}/results?huntId=${huntId}`,
      });
    });

    it("calls http service's GET with the huntId and count", () => {
      const huntId = '1234';
      const count = '10';

      httpApiService.listResultsForHunt({huntId, count}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/results?huntId=${huntId}&count=${count}`,
      });
    });

    it("calls http service's GET with the huntId and count", () => {
      const huntId = '1234';
      const count = '10';

      httpApiService.listResultsForHunt({huntId, count}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/results?huntId=${huntId}&count=${count}`,
      });
    });

    it("calls http service's GET with the huntId, count and payload type", () => {
      const huntId = '1234';
      const count = '10';
      const payloadType = 'FileFinderResult';

      httpApiService
        .listResultsForHunt({
          huntId,
          count,
          withType: payloadType,
        })
        .subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/results?huntId=${huntId}&count=${count}&with_type=${payloadType}`,
      });
    });

    it("calls http service's GET with the huntId, count, payload type and offset", () => {
      const huntId = '1234';
      const count = '10';
      const payloadType = 'FileFinderResult';
      const offset = '5';

      httpApiService
        .listResultsForHunt({
          huntId,
          count,
          withType: payloadType,
          offset,
        })
        .subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/results?huntId=${huntId}&count=${count}&with_type=${payloadType}&offset=${offset}`,
      });
    });

    it("does not call http service's GET if no huntId is specified", () => {
      const huntId = undefined;

      expect(() => httpApiService.listResultsForHunt({huntId})).toThrow(
        new Error(
          'Expected value to be non-nullable, but got undefined of type undefined.',
        ),
      );
    });
  });

  describe('listErrorsForHunt', () => {
    it("calls http service's GET with the huntId", () => {
      const huntId = '1234';

      httpApiService.listErrorsForHunt({huntId}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/errors?huntId=${huntId}`,
      });
    });

    it("calls http service's GET with the huntId and count", () => {
      const huntId = '1234';
      const count = '10';

      httpApiService.listErrorsForHunt({huntId, count}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/errors?huntId=${huntId}&count=${count}`,
      });
    });

    it("calls http service's GET with the huntId and count", () => {
      const huntId = '1234';
      const count = '10';

      httpApiService.listErrorsForHunt({huntId, count}).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/errors?huntId=${huntId}&count=${count}`,
      });
    });

    it("calls http service's GET with the huntId, count and offset", () => {
      const huntId = '1234';
      const count = '10';
      const offset = '5';

      httpApiService
        .listErrorsForHunt({
          huntId,
          count,
          offset,
        })
        .subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/errors?huntId=${huntId}&count=${count}&offset=${offset}`,
      });
    });

    it("does not call http service's GET if no huntId is specified", () => {
      const huntId = undefined;

      expect(() => httpApiService.listErrorsForHunt({huntId})).toThrow(
        new Error(
          'Expected value to be non-nullable, but got undefined of type undefined.',
        ),
      );
    });
  });

  describe('fetchHuntLogs', () => {
    it('calls http service with correct url', () => {
      const huntId = '1234';
      httpApiService.fetchHuntLogs(huntId).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/${huntId}/log`,
      });
    });
  });

  describe('fetchClientStartupInfos', () => {
    it('calls http service with correct url and params', () => {
      const clientId = 'C.1234';
      const start = new Date('2024-01-01T00:00:00Z');
      const end = new Date('2024-01-02T00:00:00Z');

      httpApiService.fetchClientStartupInfos(clientId, start, end).subscribe();

      httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/${clientId}/startup-infos?start=${start.getTime() * 1000}&end=${end.getTime() * 1000}&exclude_snapshot_collections=true`,
      });
    });
  });

  afterEach(() => {
    httpMock.verify();
  });
});
