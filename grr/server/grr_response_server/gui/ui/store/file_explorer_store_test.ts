import {TestBed} from '@angular/core/testing';
import {patchState} from '@ngrx/signals';
import {unprotected} from '@ngrx/signals/testing';

import {HttpApiWithTranslationService} from '../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../lib/api/http_api_with_translation_test_util';
import {
  newDirectory,
  newFile,
  newStatEntry,
} from '../lib/models/model_test_util';
import {
  BrowseFilesystemEntry,
  BrowseFilesystemResult,
  PathSpecPathType,
} from '../lib/models/vfs';
import {FileExplorerStore} from './file_explorer_store';

describe('FileExplorerStore', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;

  beforeEach(() => {
    httpApiService = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      providers: [
        FileExplorerStore,
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiService,
        },
      ],
    });
  });

  it('is created', () => {
    const store = TestBed.inject(FileExplorerStore);

    expect(store).toBeTruthy();
  });

  it('initializes the store with an empty root directory if the server response is undefined', () => {
    const store = TestBed.inject(FileExplorerStore);
    const fs: BrowseFilesystemResult = {
      rootEntry: undefined,
    };

    store.initialize('C.1234567890123456', '/');
    httpApiService.mockedObservables.browseFilesystem.next(fs);

    expect(store.fileSystemTree()!.file!.name).toEqual('');
    expect(store.fileSystemTree()!.file!.path).toEqual('/');
    expect(store.fileSystemTree()!.file!.isDirectory).toBeTrue();
    expect(store.fileSystemTree()!.children).toBeUndefined();
  });

  it('initializes the store with the root path', () => {
    const store = TestBed.inject(FileExplorerStore);
    const fs: BrowseFilesystemResult = {
      rootEntry: {
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newFile({
              name: 'nested_1_1',
              path: '/nested_1_1',
            }),
            children: undefined,
          },
          {
            file: newFile({
              name: 'nested_1_2',
              path: '/nested_1_2',
            }),
            children: undefined,
          },
        ],
      },
    };

    store.initialize('C.1234567890123456', '/');
    httpApiService.mockedObservables.browseFilesystem.next(fs);

    expect(httpApiService.browseFilesystem).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/',
      {includeDirectoryTree: true},
    );

    expect(store.fileSystemTree()).toEqual(fs.rootEntry);
  });

  it('raises if `fetchChildren` is called before `initialize`', () => {
    const store = TestBed.inject(FileExplorerStore);
    expect(() => {
      store.fetchChildren({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: undefined,
      });
    }).toThrowError('Client ID is not set. Call `initialize` first.');
  });

  it('fetches children of a parent', () => {
    const store = TestBed.inject(FileExplorerStore);
    const root: BrowseFilesystemEntry = {
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: undefined,
    };
    patchState(unprotected(store), {fileSystemTree: root});
    patchState(unprotected(store), {clientId: 'C.1234567890123456'});
    const listRootResult: BrowseFilesystemResult = {
      rootEntry: {
        file: root.file,
        children: [
          {
            file: newFile({
              name: 'nested_1_1',
              path: '/nested_1_1',
            }),
            children: undefined,
          },
        ],
      },
    };

    store.fetchChildren(root);
    httpApiService.mockedObservables.browseFilesystem.next(listRootResult);

    expect(httpApiService.browseFilesystem).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/',
      {includeDirectoryTree: false},
    );
    expect(store.fileSystemTree()!.file).toEqual(root.file);
    expect(store.fileSystemTree()!.children).toEqual(
      listRootResult.rootEntry!.children,
    );
  });

  it('initially sets children to undefined when initializing the store', async () => {
    const store = TestBed.inject(FileExplorerStore);
    const root: BrowseFilesystemEntry = {
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: undefined,
    };
    store.initialize('C.1234567890123456', '/');
    httpApiService.mockedObservables.browseFilesystem.next({
      rootEntry: root,
    });

    expect(httpApiService.browseFilesystem).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/',
      {includeDirectoryTree: true},
    );

    expect(store.fileSystemTree()!.children).not.toBeDefined();
  });

  it('fetchChildren sets children to an empty list if the server response is undefined', async () => {
    const store = TestBed.inject(FileExplorerStore);
    const root: BrowseFilesystemEntry = {
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: undefined,
    };
    patchState(unprotected(store), {fileSystemTree: root});
    patchState(unprotected(store), {clientId: 'C.1234567890123456'});
    const listRootResult: BrowseFilesystemResult = {
      rootEntry: {
        file: root.file,
        children: undefined,
      },
    };

    store.fetchChildren(root);
    httpApiService.mockedObservables.browseFilesystem.next(listRootResult);

    expect(httpApiService.browseFilesystem).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/',
      {includeDirectoryTree: false},
    );
    expect(store.fileSystemTree()!.file).toEqual(root.file);
    expect(store.fileSystemTree()!.children).toBeDefined();
    expect(store.fileSystemTree()!.children).toHaveSize(0);
  });

  it('refreshVfsFolder calls the http service with the correct arguments and updates the store', () => {
    const store = TestBed.inject(FileExplorerStore);
    patchState(unprotected(store), {clientId: 'C.1234567890123456'});
    const selectedFolder: BrowseFilesystemEntry = {
      file: newDirectory({
        name: 'foo',
        path: '/foo',
        stat: newStatEntry({
          pathspec: {
            path: '/foo',
            pathtype: PathSpecPathType.OS,
            segments: [],
          },
        }),
      }),
      children: undefined,
    };
    patchState(unprotected(store), {
      fileSystemTree: {
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [selectedFolder],
      },
    });
    const refreshResult: BrowseFilesystemResult = {
      rootEntry: {
        file: newFile({
          name: 'foo',
          path: '/foo',
          stat: newStatEntry({
            pathspec: {
              path: '/foo',
              pathtype: PathSpecPathType.OS,
              segments: [],
            },
          }),
        }),
        children: [
          {
            file: newFile({
              name: 'bar',
              path: '/foo/bar',
              stat: newStatEntry({
                pathspec: {
                  path: '/foo/bar',
                  pathtype: PathSpecPathType.OS,
                  segments: [],
                },
              }),
            }),
            children: undefined,
          },
        ],
      },
    };

    store.refreshVfsFolder(selectedFolder, 3);
    expect(store.currentlyRefreshingPaths()).toHaveSize(1);
    expect(store.currentlyRefreshingPaths()).toContain('/foo');

    httpApiService.mockedObservables.refreshVfsFolder.next(refreshResult);

    expect(httpApiService.refreshVfsFolder).toHaveBeenCalledWith(
      {
        clientId: 'C.1234567890123456',
        pathType: PathSpecPathType.OS,
        path: '/foo',
      },
      3,
    );
    expect(store.fileSystemTree()!.file!.name).toEqual('');
    expect(store.fileSystemTree()!.file!.path).toEqual('/');
    expect(store.fileSystemTree()!.children).toHaveSize(1);
    expect(store.fileSystemTree()!.children![0].file!.name).toEqual('foo');
    expect(store.fileSystemTree()!.children![0].file!.path).toEqual('/foo');
    expect(store.fileSystemTree()!.children![0].children).toHaveSize(1);
    expect(
      store.fileSystemTree()!.children![0].children![0].file!.name,
    ).toEqual('bar');
    expect(
      store.fileSystemTree()!.children![0].children![0].file!.path,
    ).toEqual('/foo/bar');
    expect(
      store.fileSystemTree()!.children![0].children![0].children,
    ).toBeUndefined();
    expect(store.currentlyRefreshingPaths()).toHaveSize(0);
  });
});
