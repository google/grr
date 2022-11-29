import {HttpClientTestingModule, HttpTestingController} from '@angular/common/http/testing';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {MatSnackBar} from '@angular/material/snack-bar';
import {lastValueFrom} from 'rxjs';

import {ErrorSnackBar} from '../../components/helpers/error_snackbar/error_snackbar';
import {initTestEnvironment} from '../../testing';

import {ApiBrowseFilesystemResult, ApiClientApproval, ApiFlow, ApiFlowResult, ApiGetFileDetailsResult, ApiGetVfsFileContentUpdateStateResult, ApiGetVfsFileContentUpdateStateResultState, ApiGetVfsRefreshOperationStateResult, ApiGetVfsRefreshOperationStateResultState, ApiHuntResult, ApiListClientApprovalsResult, ApiListFlowDescriptorsResult, ApiListFlowResultsResult, ApiListFlowsResult, ApiListHuntResultsResult, ApiListScheduledFlowsResult, ApiScheduledFlow, ApiUpdateVfsFileContentResult, PathSpecPathType} from './api_interfaces';
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
      imports: [
        ApiModule,
        HttpClientTestingModule,
      ],
      providers: [{provide: MatSnackBar, useFactory: () => snackbar}],
      teardown: {destroyAfterEach: false}
    });

    httpApiService = TestBed.inject(HttpApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('updateVfsFileContent posts, then polls, then gets VFS data',
     fakeAsync(async () => {
       const observable = httpApiService.updateVfsFileContent(
           'C.1234', PathSpecPathType.OS, '/foo/bar');

       // Create Promise to register a subscription, which activates the
       // Observable computation.
       const valuePromise = lastValueFrom(observable);

       // First, check that the recollection is triggered.
       const req1 = httpMock.expectOne(
           {method: 'POST', url: `${URL_PREFIX}/clients/C.1234/vfs-update`});
       expect(req1.request.body.filePath).toBe('/fs/os/foo/bar');
       const resp1: ApiUpdateVfsFileContentResult = {operationId: 'op123'};
       req1.flush(resp1);

       // Then, check that the recollection status is polled, but indicate it is
       // still running.
       tick();
       const req2 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-update/op123`
       });
       const resp2: ApiGetVfsFileContentUpdateStateResult = {
         state: ApiGetVfsFileContentUpdateStateResultState.RUNNING
       };
       req2.flush(resp2);

       // Then, check that the recollection polls again, now indicating it has
       // been completed.
       tick(httpApiService.POLLING_INTERVAL);
       // Validate that the reloading of the details is not started while
       // vfs-update still reports FINISHED.
       httpMock.expectNone(
           `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`);
       const req3 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-update/op123`
       });
       const resp3: ApiGetVfsFileContentUpdateStateResult = {
         state: ApiGetVfsFileContentUpdateStateResultState.FINISHED
       };
       req3.flush(resp3);

       // Finally, check that the new file metadata is loaded and returned.
       const req4 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`
       });
       const resp4: ApiGetFileDetailsResult = {file: {name: 'BAR'}};
       req4.flush(resp4);

       expect(await valuePromise).toEqual({name: 'BAR'});
     }));

  it('refreshVfsFolder posts, then polls, then gets VFS data',
     fakeAsync(async () => {
       const observable = httpApiService.refreshVfsFolder(
           'C.1234', PathSpecPathType.OS, '/C:/bar');

       // Create Promise to register a subscription, which activates the
       // Observable computation.
       const valuePromise = lastValueFrom(observable);

       // First, check that the recollection is triggered.
       const req1 = httpMock.expectOne({
         method: 'POST',
         url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations`
       });
       expect(req1.request.body.filePath).toBe('/fs/os/C:/bar');
       const resp1: ApiUpdateVfsFileContentResult = {operationId: 'op123'};
       req1.flush(resp1);

       // Then, check that the recollection status is polled, but indicate it is
       // still running.
       tick();
       const req2 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations/op123`
       });
       const resp2: ApiGetVfsRefreshOperationStateResult = {
         state: ApiGetVfsRefreshOperationStateResultState.RUNNING
       };
       req2.flush(resp2);

       // Then, check that the recollection polls again, now indicating it has
       // been completed.
       tick(httpApiService.POLLING_INTERVAL);
       // Validate that the reloading of the details is not started while
       // vfs-refresh-operations still reports FINISHED.
       httpMock.expectNone(`${
           URL_PREFIX}/clients/C.1234/vfs-details/fs/os/C%3A/bar?include_directory_tree=false`);
       const req3 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations/op123`
       });
       const resp3: ApiGetVfsRefreshOperationStateResult = {
         state: ApiGetVfsRefreshOperationStateResultState.FINISHED
       };
       req3.flush(resp3);

       // Finally, check that the new file metadata is loaded and returned.
       const req4 = httpMock.expectOne({
         method: 'GET',
         url: `${
             URL_PREFIX}/clients/C.1234/filesystem/C%3A/bar?include_directory_tree=false`,
       });
       const resp4: ApiBrowseFilesystemResult = {
         items: [{path: '/C:/bar', children: [{name: 'BAR'}]}]
       };
       req4.flush(resp4);

       expect(await valuePromise).toEqual({
         items: [{path: '/C:/bar', children: [{name: 'BAR'}]}]
       });
     }));

  it('subscribeToResultsForFlow polls listResultsForFlow', fakeAsync(() => {
       const values: Array<ReadonlyArray<ApiFlowResult>> = [];
       const sub = httpApiService
                       .subscribeToResultsForFlow(
                           {clientId: 'C.1234', flowId: '5678', count: 10})
                       .subscribe(result => {
                         values.push(result);
                       });

       tick();

       const req1 = httpMock.expectOne({
         method: 'GET',
         url: `${
             URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
       });
       const resp1: ApiListFlowResultsResult = {items: [{tag: 'foo'}]};
       req1.flush(resp1);

       expect(values.length).toEqual(1);
       expect(values).toEqual([[{tag: 'foo'}]]);

       tick(httpApiService.POLLING_INTERVAL);

       const req2 = httpMock.expectOne({
         method: 'GET',
         url:
             `${URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`
       });
       const resp2: ApiListFlowResultsResult = {items: [{tag: 'bar'}]};
       req2.flush(resp2);

       expect(values.length).toEqual(2);
       expect(values[1]).toEqual([{tag: 'bar'}]);

       sub.unsubscribe();

       tick(httpApiService.POLLING_INTERVAL * 2);
       // afterEach() verifies that no further request was launched.
     }));

  it('subscribeToResultsForFlow waits for result before re-polling',
     fakeAsync(() => {
       const values: Array<ReadonlyArray<ApiFlowResult>> = [];
       const sub = httpApiService
                       .subscribeToResultsForFlow(
                           {clientId: 'C.1234', flowId: '5678', count: 10})
                       .subscribe(result => {
                         values.push(result);
                       });

       tick();

       const req1 = httpMock.expectOne({
         method: 'GET',
         url: `${
             URL_PREFIX}/clients/C.1234/flows/5678/results?offset=0&count=10`,
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
       const values: Array<ReadonlyArray<ApiHuntResult>> = [];
       const sub = httpApiService
                       .subscribeToResultsForHunt({huntId: '1234', count: '10'})
                       .subscribe(result => {
                         values.push(result);
                       });

       tick();

       const req1 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`,
       });
       const resp1: ApiListHuntResultsResult = {
         items: [{clientId: 'C.1', payloadType: 'foo'}]
       };
       req1.flush(resp1);

       expect(values.length).toEqual(1);
       expect(values).toEqual([[{clientId: 'C.1', payloadType: 'foo'}]]);

       tick(httpApiService.POLLING_INTERVAL);

       const req2 = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/hunts/1234/results?huntId=1234&count=10`
       });
       const resp2: ApiListHuntResultsResult = {
         items: [{clientId: 'C.2', payloadType: 'bar'}]
       };
       req2.flush(resp2);

       expect(values.length).toEqual(2);
       expect(values[1]).toEqual([{clientId: 'C.2', payloadType: 'bar'}]);

       sub.unsubscribe();

       tick(httpApiService.POLLING_INTERVAL * 2);
       // afterEach() verifies that no further request was launched.
     }));

  it('subscribeToResultsForHunt waits for result before re-polling',
     fakeAsync(() => {
       const values: Array<ReadonlyArray<ApiHuntResult>> = [];
       const sub = httpApiService
                       .subscribeToResultsForHunt({huntId: '1234', count: '10'})
                       .subscribe(result => {
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
         items: [{clientId: 'C.1', payloadType: 'foo'}]
       };
       req1.flush(resp1);
       expect(values.length).toEqual(1);
       expect(values).toEqual([[{clientId: 'C.1', payloadType: 'foo'}]]);

       sub.unsubscribe();
     }));

  it('subscribeToScheduledFlowsForClient re-polls after scheduleFlow()',
     fakeAsync(() => {
       let lastFlows: ReadonlyArray<ApiScheduledFlow> = [];
       const sub = httpApiService
                       .subscribeToScheduledFlowsForClient('C.1234', 'testuser')
                       .subscribe((flows) => {
                         lastFlows = flows;
                       });

       tick();

       httpMock
           .expectOne({
             method: 'GET',
             url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser/`,
           })
           .flush({});

       httpApiService.scheduleFlow('C.1234', 'TestFlow', {}).subscribe();

       httpMock
           .expectOne({
             method: 'GET',
             url: `${URL_PREFIX}/flows/descriptors`,
           })
           .flush({
             items: [{category: 'Test', name: 'TestFlow', defaultArgs: {}}]
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
             url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser/`,
           })
           .flush(
               {scheduledFlows: [{scheduledFlowId: '123'}]} as
               ApiListScheduledFlowsResult);

       expect(lastFlows).toEqual([{scheduledFlowId: '123'}]);
       httpMock.verify();
       sub.unsubscribe();
     }));

  it('subscribeToFlowsForClient re-polls after startFlow()', fakeAsync(() => {
       let lastFlows: ReadonlyArray<ApiFlow> = [];
       const sub =
           httpApiService
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
             items: [{category: 'Test', name: 'TestFlow', defaultArgs: {}}]
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
       let lastFlows: ReadonlyArray<ApiFlow> = [];
       const sub =
           httpApiService
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

  it('subscribeToScheduledFlowsForClient re-polls after unscheduleFlow()',
     fakeAsync(() => {
       let lastFlows: ReadonlyArray<ApiScheduledFlow> = [];
       const sub = httpApiService
                       .subscribeToScheduledFlowsForClient('C.1234', 'testuser')
                       .subscribe((flows) => {
                         lastFlows = flows;
                       });

       tick();

       httpMock
           .expectOne({
             method: 'GET',
             url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser/`,
           })
           .flush({});

       httpApiService.unscheduleFlow('C.1234', '123').subscribe();

       httpMock
           .expectOne({
             method: 'DELETE',
             url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/123/`,
           })
           .flush({});

       httpMock
           .expectOne({
             method: 'GET',
             url: `${URL_PREFIX}/clients/C.1234/scheduled-flows/testuser/`,
           })
           .flush(
               {scheduledFlows: [{scheduledFlowId: '456'}]} as
               ApiListScheduledFlowsResult);

       expect(lastFlows).toEqual([{scheduledFlowId: '456'}]);
       httpMock.verify();
       sub.unsubscribe();
     }));

  it('subscribeToListApprovals re-polls after requestApproval()',
     fakeAsync(() => {
       let lastApprovals: ReadonlyArray<ApiClientApproval> = [];
       const sub = httpApiService.subscribeToListApprovals('C.1234').subscribe(
           (approvals) => {
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
           .requestApproval(
               {approvers: [], cc: [], clientId: 'C.1234', reason: ''})
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
          method: 'POST'
        })
        .flush({message: 'testerror'}, {status: 500, statusText: 'Error'});

    expect(snackbar.openFromComponent)
        .toHaveBeenCalledOnceWith(ErrorSnackBar, jasmine.objectContaining({
          data: jasmine.stringMatching('testerror')
        }));
  });

  it('getFileDetails handles Windows paths correctly', fakeAsync(() => {
       httpApiService
           .getFileDetails('C.1234', PathSpecPathType.TSK, 'C:/Windows/foo')
           .subscribe();

       const req = httpMock.expectOne({
         method: 'GET',
         url:
             `${URL_PREFIX}/clients/C.1234/vfs-details/fs/tsk/C%3A/Windows/foo`,
       });

       // Dummy assertion to prevent warnings about missing assertions.
       expect(req).toBeTruthy();
       req.flush({});
     }));

  it('getFileDetails handles root', fakeAsync(() => {
       httpApiService.getFileDetails('C.1234', PathSpecPathType.OS, '/')
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
       httpApiService.getFileDetails('C.1234', PathSpecPathType.OS, '/foo/bar')
           .subscribe();

       const req = httpMock.expectOne({
         method: 'GET',
         url: `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`,
       });

       // Dummy assertion to prevent warnings about missing assertions.
       expect(req).toBeTruthy();
       req.flush({});
     }));

  afterEach(() => {
    httpMock.verify();
  });
});
