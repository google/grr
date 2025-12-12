import {TestBed} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {ApiGetFileTextArgsEncoding} from '../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {newFile} from '../lib/models/model_test_util';
import {File, PathSpecPathType} from '../lib/models/vfs';
import {FileStore} from './file_store';

describe('File Store', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;
  let fileStore: InstanceType<typeof FileStore>;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        FileStore,
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
      teardown: {destroyAfterEach: true},
    });

    fileStore = TestBed.inject(FileStore);
  });

  it('fetches file content access and stores them in the fileContentAccessMap', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
    };

    fileStore.fetchFileContentAccess(fileSpec);
    httpApiService.mockedObservables.getFileAccess.next(true);

    expect(fileStore.fileContentAccessMap()).toHaveSize(1);
    expect(
      fileStore
        .fileContentAccessMap()!
        .get('C.1234')!
        .get(PathSpecPathType.OS)!
        .get('/foo/bar'),
    ).toEqual(true);
  });

  it('fetches file details and stores them in the fileDetailsMap', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      hasFileContentAccess: true,
    };

    fileStore.fetchFileDetails(fileSpec);
    const file: File = newFile({});
    httpApiService.mockedObservables.getFileDetails.next(file);

    expect(fileStore.fileDetailsMap()).toHaveSize(1);
    expect(
      fileStore
        .fileDetailsMap()!
        .get('C.1234')!
        .get(PathSpecPathType.OS)!
        .get('/foo/bar'),
    ).toEqual(file);
  });

  it('does not fetch file details if no access to the file', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      hasFileContentAccess: false,
    };

    fileStore.fetchFileDetails(fileSpec);

    expect(httpApiService.getFileDetails).not.toHaveBeenCalled();
    expect(fileStore.fileDetailsMap()).toHaveSize(0);
  });

  it('fetches file text and stores them in the fileTextMap', () => {
    fileStore.fetchTextFile({
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      offset: 0,
      length: 1024,
      hasFileContentAccess: true,
    });
    const fileText = 'foo bar';
    httpApiService.mockedObservables.getFileText.next({
      textContent: fileText,
      totalLength: BigInt(fileText.length),
    });

    expect(fileStore.fileTextMap()).toHaveSize(1);
    expect(
      fileStore
        .fileTextMap()!
        .get('C.1234')!
        .get(PathSpecPathType.OS)!
        .get('/foo/bar'),
    ).toEqual({textContent: fileText, totalLength: BigInt(fileText.length)});
  });

  it('does not fetch file text if no access to the file', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      hasFileContentAccess: false,
    };

    fileStore.fetchTextFile(fileSpec);

    expect(httpApiService.getFileText).not.toHaveBeenCalled();
    expect(fileStore.fileTextMap()).toHaveSize(0);
  });

  it('fetches file blob and stores them in the fileBlobMap', () => {
    fileStore.fetchBinaryFile({
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      offset: 0,
      length: 1024,
      hasFileContentAccess: true,
    });
    const fileBlob = new Uint8Array([1, 2, 3, 4, 5]).buffer;
    httpApiService.mockedObservables.getFileBlob.next(fileBlob);
    httpApiService.mockedObservables.getFileBlobLength.next(
      BigInt(fileBlob.byteLength),
    );

    expect(fileStore.fileBlobMap()).toHaveSize(1);
    expect(
      fileStore
        .fileBlobMap()!
        .get('C.1234')!
        .get(PathSpecPathType.OS)!
        .get('/foo/bar'),
    ).toEqual({
      blobContent: fileBlob,
      totalLength: BigInt(fileBlob.byteLength),
    });
  });

  it('does not fetch file blob if no access to the file', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
      hasFileContentAccess: false,
    };

    fileStore.fetchBinaryFile(fileSpec);

    expect(httpApiService.getFileBlob).not.toHaveBeenCalled();
    expect(fileStore.fileBlobMap()).toHaveSize(0);
  });

  it('recollects file and updates the fileDetailsMap and fetches the file text and blob', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/updated',
    };
    const file = newFile({});

    fileStore.recollectFile(fileSpec);
    httpApiService.mockedObservables.updateVfsFileContent.next(file);

    expect(
      fileStore
        .fileDetailsMap()!
        .get('C.1234')!
        .get(PathSpecPathType.OS)!
        .get('/foo/updated'),
    ).toEqual(file);
    expect(httpApiService.getFileText).toHaveBeenCalledWith(fileSpec, {
      offset: '0',
      length: '1024',
      encoding: ApiGetFileTextArgsEncoding.UTF_8,
    });
    expect(httpApiService.getFileBlob).toHaveBeenCalledWith(fileSpec, {
      offset: '0',
      length: '1024',
    });
  });

  it('adds file to recollectingFiles while recollecting file', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/updated',
    };

    fileStore.recollectFile(fileSpec);

    expect(fileStore.recollectingFiles()).toHaveSize(1);
    expect(fileStore.recollectingFiles()).toContain(fileSpec);
    httpApiService.mockedObservables.updateVfsFileContent.next(newFile({}));
    expect(fileStore.recollectingFiles()).toHaveSize(0);
  });

  it('returns true if file is being recollected when isRecollecting is called', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/updated',
    };

    const store = TestBed.inject(FileStore);
    patchState(unprotected(store), {
      recollectingFiles: new Set([fileSpec]),
    });

    expect(store.isRecollecting(fileSpec)).toBeTrue();
  });

  it('returns false if file is not being recollected when isRecollecting is called', () => {
    const fileSpec = {
      clientId: 'C.1234',
      pathType: PathSpecPathType.OS,
      path: '/foo/updated',
    };

    const store = TestBed.inject(FileStore);
    patchState(unprotected(store), {recollectingFiles: new Set([])});

    expect(store.isRecollecting(fileSpec)).toBeFalse();
  });

  it('initializes the store with empty maps', () => {
    // Having this test in the end improves the chance of catching the
    // mutation of the state in the other tests.
    expect(fileStore.fileDetailsMap()).toHaveSize(0);
    expect(fileStore.fileTextMap()).toHaveSize(0);
    expect(fileStore.fileBlobMap()).toHaveSize(0);
  });
});
