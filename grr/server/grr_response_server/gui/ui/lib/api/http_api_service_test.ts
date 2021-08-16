import {HttpClientTestingModule, HttpTestingController} from '@angular/common/http/testing';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {lastValueFrom} from 'rxjs';

import {ApiGetFileDetailsResult, ApiGetVfsFileContentUpdateStateResult, ApiGetVfsFileContentUpdateStateResultState, ApiUpdateVfsFileContentResult, PathSpecPathType} from './api_interfaces';
import {HttpApiService, URL_PREFIX} from './http_api_service';
import {ApiModule} from './module';



initTestEnvironment();

describe('HttpApiService', () => {
  let httpApiService: HttpApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        ApiModule,
        HttpClientTestingModule,
      ],
      providers: [],
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

  afterEach(() => {
    httpMock.verify();
  });
});
