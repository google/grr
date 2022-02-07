import {HttpClientTestingModule, HttpTestingController} from '@angular/common/http/testing';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {MatSnackBar} from '@angular/material/snack-bar';
import {lastValueFrom} from 'rxjs';

import {ErrorSnackbar} from '../../components/helpers/error_snackbar/error_snackbar';
import {initTestEnvironment} from '../../testing';

import {ApiFlowResult, ApiGetFileDetailsResult, ApiGetVfsFileContentUpdateStateResult, ApiGetVfsFileContentUpdateStateResultState, ApiGetVfsRefreshOperationStateResult, ApiGetVfsRefreshOperationStateResultState, ApiListFilesResult, ApiListFlowResultsResult, ApiUpdateVfsFileContentResult, PathSpecPathType} from './api_interfaces';
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
           'C.1234', PathSpecPathType.OS, '/foo/bar');

       // Create Promise to register a subscription, which activates the
       // Observable computation.
       const valuePromise = lastValueFrom(observable);

       // First, check that the recollection is triggered.
       const req1 = httpMock.expectOne({
         method: 'POST',
         url: `${URL_PREFIX}/clients/C.1234/vfs-refresh-operations`
       });
       expect(req1.request.body.filePath).toBe('/fs/os/foo/bar');
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
       httpMock.expectNone(
           `${URL_PREFIX}/clients/C.1234/vfs-details/fs/os/foo/bar`);
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
         url: `${URL_PREFIX}/clients/C.1234/vfs-index/fs/os/foo/bar`
       });
       const resp4: ApiListFilesResult = {items: [{name: 'BAR'}]};
       req4.flush(resp4);

       expect(await valuePromise).toEqual({items: [{name: 'BAR'}]});
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
        .toHaveBeenCalledOnceWith(ErrorSnackbar, jasmine.objectContaining({
          data: jasmine.stringMatching('testerror')
        }));
  });

  afterEach(() => {
    httpMock.verify();
  });
});
