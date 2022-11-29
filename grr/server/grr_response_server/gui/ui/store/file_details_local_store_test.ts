import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom, Subject} from 'rxjs';

import {PathSpecPathType} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {injectHttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {arrayBufferOf} from '../lib/type_utils';
import {initTestEnvironment} from '../testing';

import {ContentFetchMode, FileDetailsLocalStore} from './file_details_local_store';



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
          teardown: {destroyAfterEach: false}
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

       httpApiService.mockedObservables.updateVfsFileContent.next({
         isDirectory: false,
         name: 'bar',
         path: 'fs/os/foo/bar',
         stat: {pathspec: {path: '/foo/bar', pathtype: PathSpecPathType.OS}},
         age: '123',
       });
       httpApiService.mockedObservables.updateVfsFileContent.complete();

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

       httpApiService.mockedObservables.updateVfsFileContent.next({
         isDirectory: false,
         name: 'BAR',
         path: 'fs/os/foo/bar',
         stat: {pathspec: {path: '/foo/bar', pathtype: PathSpecPathType.OS}},
         age: '123',
       });
       httpApiService.mockedObservables.updateVfsFileContent.complete();

       expect(await firstValueFrom(fileDetailsLocalStore.details$))
           .toEqual(jasmine.objectContaining({name: 'BAR'}));
     }));

  it('recollectFile reloads text file contents', fakeAsync(async () => {
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
           {content: '123', totalSize: '12'});

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(4));
       httpApiService.mockedObservables.getFileText.next(
           {content: '4567', totalSize: '12'});

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.recollectFile();
       httpApiService.mockedObservables.updateVfsFileContent.next({
         isDirectory: false,
         path: 'fs/os/foo/bar',
         name: 'BAR',
         stat: {pathspec: {path: '/foo/bar', pathtype: PathSpecPathType.OS}},
         age: '123',
       });
       httpApiService.mockedObservables.getFileText.next(
           {content: 'abcdefg', totalSize: '12'});

       expect(httpApiService.getFileText)
           .toHaveBeenCalledWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: '0', length: '7'}));
       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('abcdefg');
     }));

  it('recollectFile reloads blob file contents', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });
       fileDetailsLocalStore.setMode(ContentFetchMode.BLOB);

       httpApiService.mockedObservables.getFileBlob = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(2));
       httpApiService.mockedObservables.getFileBlobLength.next(BigInt(10));
       httpApiService.mockedObservables.getFileBlob.next(arrayBufferOf([1, 2]));

       httpApiService.mockedObservables.getFileBlob = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(3));
       httpApiService.mockedObservables.getFileBlob.next(
           arrayBufferOf([3, 4, 5]));

       httpApiService.mockedObservables.getFileBlob = new Subject();
       fileDetailsLocalStore.recollectFile();
       httpApiService.mockedObservables.updateVfsFileContent.next({
         isDirectory: false,
         path: 'fs/os/foo/bar',
         name: 'BAR',
         stat: {pathspec: {path: '/foo/bar', pathtype: PathSpecPathType.OS}},
         age: '123',
       });
       const NEW_LENGTH = BigInt(12);
       httpApiService.mockedObservables.getFileBlobLength.next(NEW_LENGTH);
       httpApiService.mockedObservables.getFileBlob.next(
           arrayBufferOf([55, 4, 3, 2, 1]));

       expect(httpApiService.getFileBlob)
           .toHaveBeenCalledWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: '0', length: '5'}));
       expect(await firstValueFrom(fileDetailsLocalStore.totalLength$))
           .toEqual(NEW_LENGTH);
       expect(await firstValueFrom(fileDetailsLocalStore.blobContent$))
           .toEqual(arrayBufferOf([55, 4, 3, 2, 1]));
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
               jasmine.objectContaining({offset: '0', length: '3'}));
       httpApiService.getFileText.calls.reset();

       httpApiService.mockedObservables.getFileText.next(
           {content: '123', totalSize: '12'});

       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('123');

       httpApiService.mockedObservables.getFileText = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(4));

       expect(httpApiService.getFileText)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: '3', length: '4'}));

       httpApiService.mockedObservables.getFileText.next(
           {content: '4567', totalSize: '12'});

       expect(await firstValueFrom(fileDetailsLocalStore.textContent$))
           .toBe('1234567');
     }));

  it('fetchMoreContent appends blob contents', fakeAsync(async () => {
       const fileDetailsLocalStore = TestBed.inject(FileDetailsLocalStore);
       const httpApiService = injectHttpApiServiceMock();

       fileDetailsLocalStore.selectFile({
         clientId: 'C.1234',
         pathType: PathSpecPathType.OS,
         path: '/foo/bar'
       });
       fileDetailsLocalStore.setMode(ContentFetchMode.BLOB);

       httpApiService.mockedObservables.getFileBlob = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(2));

       expect(httpApiService.getFileBlob)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: '0', length: '2'}));
       httpApiService.getFileBlob.calls.reset();

       httpApiService.mockedObservables.getFileBlobLength.next(BigInt(10));
       httpApiService.mockedObservables.getFileBlob.next(
           arrayBufferOf([128, 5]));

       expect(await firstValueFrom(fileDetailsLocalStore.blobContent$))
           .toEqual(arrayBufferOf([128, 5]));

       httpApiService.mockedObservables.getFileBlob = new Subject();
       fileDetailsLocalStore.fetchMoreContent(BigInt(3));

       expect(httpApiService.getFileBlob)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/foo/bar',
               jasmine.objectContaining({offset: '2', length: '3'}));

       httpApiService.mockedObservables.getFileBlob.next(
           arrayBufferOf([5, 6, 7]));

       expect(await firstValueFrom(fileDetailsLocalStore.blobContent$))
           .toEqual(arrayBufferOf([128, 5, 5, 6, 7]));
     }));
});
