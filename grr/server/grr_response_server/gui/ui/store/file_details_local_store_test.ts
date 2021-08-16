import {fakeAsync, TestBed} from '@angular/core/testing';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FileDetailsLocalStore} from '@app/store/file_details_local_store';
import {initTestEnvironment} from '@app/testing';
import {firstValueFrom, Subject} from 'rxjs';

import {PathSpecPathType} from '../lib/api/api_interfaces';
import {injectHttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';



initTestEnvironment();


describe('FileDetailsLocalStore', () => {
  beforeEach(() => {
    TestBed
        .configureTestingModule({
          imports: [],
          providers: [
            FileDetailsLocalStore,
            {provide: HttpApiService, useFactory: mockHttpApiService},
          ],
        })
        .compileComponents();
  });

  it('recollectFile sets isRecollecting', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });
       fileDetailsLocalStore.recollectFile();

       expect(await firstValueFrom(fileDetailsLocalStore.isRecollecting$))
           .toBeTrue();
       expect(httpApiService.updateVfsFileContent)
           .toHaveBeenCalledOnceWith('C.1234', PathSpecPathType.OS, '/foo/bar');

       httpApiService.mockedObservables.updateVfsFileContent.next(
           {stat: {pathspec: {path: '/foo/bar'}}});

       expect(await firstValueFrom(fileDetailsLocalStore.isRecollecting$))
           .toBeFalse();
     }));

  it('recollectFile calls updateVfsFileContent', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });
       fileDetailsLocalStore.recollectFile();

       expect(httpApiService.updateVfsFileContent)
           .toHaveBeenCalledOnceWith('C.1234', PathSpecPathType.OS, '/foo/bar');

       httpApiService.mockedObservables.updateVfsFileContent.next(
           {name: 'BAR', stat: {pathspec: {path: '/foo/bar'}}});

       expect(await firstValueFrom(fileDetailsLocalStore.details$))
           .toEqual(jasmine.objectContaining({name: 'BAR'}));
     }));

  it('recollectFile reloads file contents', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(3));
       httpApiService.mockedObservables.getFileText.next(
           {content: '123', totalSize: 12});

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(4));
       httpApiService.mockedObservables.getFileText.next(
           {content: '4567', totalSize: 12});

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.recollectFile();
       httpApiService.mockedObservables.updateVfsFileContent.next(
           {name: 'BAR', stat: {pathspec: {path: '/foo/bar'}}});
       httpApiService.mockedObservables.getFileText.next(
           {content: 'abcdefg', totalSize: 12});

       expect(httpApiService.getFileText)
           .toHaveBeenCalledWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: 0, length: BigInt(7)}));
       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('abcdefg');
     }));

  it('fetchMoreContent appends file contents', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(3));

       expect(httpApiService.getFileText)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: 0, length: BigInt(3)}));
       httpApiService.getFileText.calls.reset();

       httpApiService.mockedObservables.getFileText.next(
           {content: '123', totalSize: 12});

       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('123');

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(4));

       expect(httpApiService.getFileText)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: 3, length: BigInt(4)}));

       httpApiService.mockedObservables.getFileText.next(
           {content: '4567', totalSize: 12});

       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('1234567');
     }));
});
