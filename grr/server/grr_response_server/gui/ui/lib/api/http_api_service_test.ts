import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import {TestBed, fakeAsync, tick} from '@angular/core/testing';
import {MatSnackBar} from '@angular/material/snack-bar';
import {lastValueFrom} from 'rxjs';

import {ErrorSnackBar} from '../../components/helpers/error_snackbar/error_snackbar';
import {initTestEnvironment} from '../../testing';

import {
  ApiBrowseFilesystemResult,
  ApiClientApproval,
  ApiCountHuntResultsByTypeResult,
  ApiFlow,
  ApiFlowResult,
  ApiGetFileDetailsResult,
  ApiGetHuntClientCompletionStatsResult,
  ApiGetVfsFileContentUpdateStateResult,
  ApiGetVfsFileContentUpdateStateResultState,
  ApiGetVfsRefreshOperationStateResult,
  ApiGetVfsRefreshOperationStateResultState,
  ApiHuntResult,
  ApiListClientApprovalsResult,
  ApiListFlowDescriptorsResult,
  ApiListFlowResultsResult,
  ApiListFlowsResult,
  ApiListHuntResultsResult,
  ApiListScheduledFlowsResult,
  ApiScheduledFlow,
  ApiUpdateVfsFileContentResult,
  PathSpecPathType,
} from './api_interfaces';
import {HttpApiService, URL_PREFIX} from './http_api_service';
import {ApiModule} from './module';

initTestEnvironment();

describe('HttpApiService', () => {
  let httpApiService: HttpApiService;
  let httpMock: HttpTestingController;
  let snackbar: Partial<MatSnackBar>;

  beforeEach(() => {
    snackbar = jasmine.createSpyObj('MatSnackBar', ['openFromComponent']);

    TestBed.configureTestingModule({
      imports: [ApiModule, HttpClientTestingModule],
      providers: [{provide: MatSnackBar, useFactory: () => snackbar}],
      teardown: {destroyAfterEach: false},
    });

    httpApiService = TestBed.inject(HttpApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('updateVfsFileContent posts, then polls, then gets VFS data', fakeAsync(async () => {
    const observable = httpApiService.updateVfsFileContent(
      'C.1234',
      PathSpecPathType.OS,
      '/foo/bar',
    );

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
    tick(httpApiService.POLLING_INTERVAL);
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

    expect(await valuePromise).toEqual({name: 'BAR'});
  }));

  it('refreshVfsFolder posts, then polls, then gets VFS data', fakeAsync(async () => {
    const observable = httpApiService.refreshVfsFolder(
      'C.1234',
      PathSpecPathType.OS,
      '/C:/bar',
    );

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
    tick(httpApiService.POLLING_INTERVAL);
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
      items: [{path: '/C:/bar', children: [{name: 'BAR'}]}],
    };
    req4.flush(resp4);

    expect(await valuePromise).toEqual({
      items: [{path: '/C:/bar', children: [{name: 'BAR'}]}],
    });
  }));

  it('subscribeToResultsForFlow polls listResultsForFlow', fakeAsync(() => {
    const values: Array<readonly ApiFlowResult[]> = [];
    const sub = httpApiService
      .subscribeToResultsForFlow({
        clientId: 'C.1234',
        flowId: '5678',
        count: 10,
      })
      .subscribe((result) => {
        values.push(result);
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

    tick(httpApiService.POLLING_INTERVAL);

    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
    });
    const resp2: ApiListFlowResultsResult = {items: [{tag: 'bar'}]};
    req2.flush(resp2);

    expect(values.length).toEqual(2);
    expect(values[1]).toEqual([{tag: 'bar'}]);

    sub.unsubscribe();

    tick(httpApiService.POLLING_INTERVAL * 2);
    // afterEach() verifies that no further request was launched.
  }));

  it('subscribeToResultsForFlow waits for result before re-polling', fakeAsync(() => {
    const values: Array<readonly ApiFlowResult[]> = [];
    const sub = httpApiService
      .subscribeToResultsForFlow({
        clientId: 'C.1234',
        flowId: '5678',
        count: 10,
      })
      .subscribe((result) => {
        values.push(result);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
    });

    tick(httpApiService.POLLING_INTERVAL * 2);

    httpMock.verify();

    const resp1: ApiListFlowResultsResult = {items: [{tag: 'foo'}]};
    req1.flush(resp1);
    expect(values.length).toEqual(1);
    expect(values).toEqual([[{tag: 'foo'}]]);

    sub.unsubscribe();
  }));

  it('subscribeToResultsForHunt polls listResultsForHunt', fakeAsync(() => {
    const values: Array<readonly ApiHuntResult[]> = [];
    const sub = httpApiService
      .subscribeToResultsForHunt({huntId: '1234', count: '10'})
      .subscribe((result) => {
        values.push(result);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });
    const resp1: ApiListHuntResultsResult = {
      items: [{clientId: 'C.1'}],
    };
    req1.flush(resp1);

    expect(values.length).toEqual(1);
    expect(values).toEqual([[{clientId: 'C.1'}]]);

    tick(httpApiService.POLLING_INTERVAL);

    const req2 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });
    const resp2: ApiListHuntResultsResult = {
      items: [{clientId: 'C.2'}],
    };
    req2.flush(resp2);

    expect(values.length).toEqual(2);
    expect(values[1]).toEqual([{clientId: 'C.2'}]);

    sub.unsubscribe();

    tick(httpApiService.POLLING_INTERVAL * 2);
    // afterEach() verifies that no further request was launched.
  }));

  it('subscribeToResultsForHunt waits for result before re-polling', fakeAsync(() => {
    const values: Array<readonly ApiHuntResult[]> = [];
    const sub = httpApiService
      .subscribeToResultsForHunt({huntId: '1234', count: '10'})
      .subscribe((result) => {
        values.push(result);
      });

    tick();

    const req1 = httpMock.expectOne({
      method: 'GET',
      url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
    });

    tick(httpApiService.POLLING_INTERVAL * 2);

    httpMock.verify();

    const resp1: ApiListHuntResultsResult = {
      items: [{clientId: 'C.1'}],
    };
    req1.flush(resp1);
    expect(values.length).toEqual(1);
    expect(values).toEqual([[{clientId: 'C.1'}]]);

    sub.unsubscribe();
  }));

  it('subscribeToScheduledFlowsForClient re-polls after scheduleFlow()', fakeAsync(() => {
    let lastFlows: readonly ApiScheduledFlow[] = [];
    const sub = httpApiService
      .subscribeToScheduledFlowsForClient('C.1234', 'testuser')
      .subscribe((flows) => {
        lastFlows = flows;
      });

    tick();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser`,
      })
      .flush({});

    httpApiService.scheduleFlow('C.1234', 'TestFlow', {}).subscribe();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/flows/descriptors`,
      })
      .flush({
        items: [{category: 'Test', name: 'TestFlow', defaultArgs: {}}],
      } as ApiListFlowDescriptorsResult);

    httpMock
      .expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows`,
      })
      .flush({});

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser`,
      })
      .flush({
        scheduledFlows: [{scheduledFlowId: '123'}],
      } as ApiListScheduledFlowsResult);

    expect(lastFlows).toEqual([{scheduledFlowId: '123'}]);
    httpMock.verify();
    sub.unsubscribe();
  }));

  it('subscribeToFlowsForClient re-polls after startFlow()', fakeAsync(() => {
    let lastFlows: readonly ApiFlow[] = [];
    const sub = httpApiService
      .subscribeToFlowsForClient({clientId: 'C.1234', count: '10'})
      .subscribe((flows) => {
        lastFlows = flows;
      });

    tick();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/flows?count=10`,
      })
      .flush({});

    httpApiService.startFlow('C.1234', 'TestFlow', {}).subscribe();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/flows/descriptors`,
      })
      .flush({
        items: [{category: 'Test', name: 'TestFlow', defaultArgs: {}}],
      } as ApiListFlowDescriptorsResult);

    httpMock
      .expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/clients/C.1234/flows`,
      })
      .flush({});

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/flows?count=10`,
      })
      .flush({items: [{flowId: '123'}]} as ApiListFlowsResult);

    expect(lastFlows).toEqual([{flowId: '123'}]);
    httpMock.verify();
    sub.unsubscribe();
  }));

  it('subscribeToFlowsForClient re-polls after cancelFlow()', fakeAsync(() => {
    let lastFlows: readonly ApiFlow[] = [];
    const sub = httpApiService
      .subscribeToFlowsForClient({clientId: 'C.1234', count: '10'})
      .subscribe((flows) => {
        lastFlows = flows;
      });

    tick();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/flows?count=10`,
      })
      .flush({});

    httpApiService.cancelFlow('C.1234', '123').subscribe();

    httpMock
      .expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/clients/C.1234/flows/123/actions/cancel`,
      })
      .flush({});

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/flows?count=10`,
      })
      .flush({items: [{flowId: '456'}]} as ApiListFlowsResult);

    expect(lastFlows).toEqual([{flowId: '456'}]);
    httpMock.verify();
    sub.unsubscribe();
  }));

  it('subscribeToScheduledFlowsForClient re-polls after unscheduleFlow()', fakeAsync(() => {
    let lastFlows: readonly ApiScheduledFlow[] = [];
    const sub = httpApiService
      .subscribeToScheduledFlowsForClient('C.1234', 'testuser')
      .subscribe((flows) => {
        lastFlows = flows;
      });

    tick();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser`,
      })
      .flush({});

    httpApiService.unscheduleFlow('C.1234', '123').subscribe();

    httpMock
      .expectOne({
        method: 'DELETE',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/123`,
      })
      .flush({});

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser`,
      })
      .flush({
        scheduledFlows: [{scheduledFlowId: '456'}],
      } as ApiListScheduledFlowsResult);

    expect(lastFlows).toEqual([{scheduledFlowId: '456'}]);
    httpMock.verify();
    sub.unsubscribe();
  }));

  it('subscribeToListApprovals re-polls after requestApproval()', fakeAsync(() => {
    let lastApprovals: readonly ApiClientApproval[] = [];
    const sub = httpApiService
      .subscribeToListClientApprovals('C.1234')
      .subscribe((approvals) => {
        lastApprovals = approvals;
      });

    tick();

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/users/me/approvals/client/C.1234`,
      })
      .flush({});

    httpApiService
      .requestClientApproval({
        approvers: [],
        cc: [],
        clientId: 'C.1234',
        reason: '',
      })
      .subscribe();

    httpMock
      .expectOne({
        method: 'POST',
        url: `${URL_PREFIX}/users/me/approvals/client/C.1234`,
      })
      .flush({});

    httpMock
      .expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/users/me/approvals/client/C.1234`,
      })
      .flush({items: [{id: '456'}]} as ApiListClientApprovalsResult);

    expect(lastApprovals).toEqual([{id: '456'}]);
    httpMock.verify();
    sub.unsubscribe();
  }));

  it('shows a snackbar with the error message on HTTP errors', async () => {
    httpApiService.cancelFlow('C.1234', '5678').subscribe({
      error: () => {},
    });

    httpMock
      .expectOne({
        url: `${URL_PREFIX}/clients/C.1234/flows/5678/actions/cancel`,
        method: 'POST',
      })
      .flush({message: 'testerror'}, {status: 500, statusText: 'Error'});

    expect(snackbar.openFromComponent).toHaveBeenCalledOnceWith(
      ErrorSnackBar,
      jasmine.objectContaining({
        data: jasmine.stringMatching('testerror'),
      }),
    );
  });

  it('getFileDetails handles Windows paths correctly', fakeAsync(() => {
    httpApiService
      .getFileDetails('C.1234', PathSpecPathType.TSK, 'C:/Windows/foo')
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
      .getFileDetails('C.1234', PathSpecPathType.OS, '/')
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
      .getFileDetails('C.1234', PathSpecPathType.OS, '/foo/bar')
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

  describe('subscribeToHuntClientCompletionStats', () => {
    it(`Doesn't send a "size" HTTPParam if not specified`, fakeAsync(() => {
      const sub = httpApiService
        .subscribeToHuntClientCompletionStats({huntId: '1234', size: undefined})
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
        .subscribeToHuntClientCompletionStats({huntId: '1234', size: '10'})
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

      tick(httpApiService.POLLING_INTERVAL);

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

      tick(httpApiService.POLLING_INTERVAL * 2);
      // afterEach() verifies that no further request was launched.
    }));

    it('Waits for result before re-polling', fakeAsync(() => {
      const values: ApiGetHuntClientCompletionStatsResult[] = [];
      const sub = httpApiService
        .subscribeToHuntClientCompletionStats({huntId: '1234', size: '10'})
        .subscribe((result) => {
          values.push(result);
        });

      tick();

      const req1 = httpMock.expectOne({
        method: 'GET',
        url: `${URL_PREFIX}/hunts/1234/client-completion-stats?size=10`,
      });

      tick(httpApiService.POLLING_INTERVAL * 2);

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

  describe('subscribeToHuntResultsCountByType', () => {
    it('polls getHuntResultsByType', fakeAsync(() => {
      const huntId = '1234';
      let resultsByType: ApiCountHuntResultsByTypeResult = {};
      const sub = httpApiService
        .subscribeToHuntResultsCountByType(huntId)
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

      tick(httpApiService.POLLING_INTERVAL);

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

      tick(httpApiService.POLLING_INTERVAL * 2);
      // afterEach() verifies that no further request was launched.
    }));

    it('Waits for result before re-polling', fakeAsync(() => {
      const huntId = '1234';
      let resultsByType: ApiCountHuntResultsByTypeResult = {};
      const sub = httpApiService
        .subscribeToHuntResultsCountByType(huntId)
        .subscribe((result) => {
          resultsByType = result;
        });

      tick(httpApiService.POLLING_INTERVAL * 2);

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

  afterEach(() => {
    httpMock.verify();
  });
});
