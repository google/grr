import {TestBed} from '@angular/core/testing';
import {firstValueFrom, of, Subject} from 'rxjs';

import {ApiFile, ApiListFilesResult, PathSpecPathType} from '../lib/api/api_interfaces';
import {HttpApiService} from '../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {initTestEnvironment} from '../testing';

import {VfsViewLocalStore} from './vfs_view_local_store';

initTestEnvironment();

const apiDir = (path: string): ApiFile => ({
  path: `fs/os${path}`,
  name: path.slice(path.lastIndexOf('/') + 1),
  isDirectory: true,
});

const apiFile =
    (path: string, pathtype: PathSpecPathType = PathSpecPathType.OS): ApiFile =>
        ({
          path: `fs/${pathtype.toLowerCase()}${path}`,
          name: path.slice(path.lastIndexOf('/') + 1),
          isDirectory: false,
          stat: {pathspec: {path, pathtype}},
          age: 123,
        });

describe('VfsViewLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let vfsViewLocalStore: VfsViewLocalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        VfsViewLocalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false}
    });

    vfsViewLocalStore = TestBed.inject(VfsViewLocalStore);
  });

  it('navigateToPath lists files from API', async () => {
    const listFiles: HttpApiService['listFiles'] = (clientId, pathType, path) =>
        of(pathType === PathSpecPathType.OS ? {items: [apiDir('/foo')]} : {});
    httpApiService.listFiles =
        jasmine.createSpy('listFiles').and.callFake(listFiles);

    expect(httpApiService.listFiles).not.toHaveBeenCalled();

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    expect(httpApiService.listFiles).toHaveBeenCalledTimes(3);
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.TSK, '/');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.NTFS, '/');

    const tree = await firstValueFrom(vfsViewLocalStore.directoryTree$);
    expect(tree).toEqual(
        jasmine.objectContaining({
          path: '/',
          children: [
            jasmine.objectContaining({path: '/foo'}),
          ]
        }),
    );
  });

  it('navigateToPath lists all parent paths', async () => {
    expect(httpApiService.listFiles).not.toHaveBeenCalled();

    httpApiService.listFiles =
        jasmine.createSpy('listFiles')
            .and.callFake((clientId, pathType, path) => {
              if (path === '/') {
                return of({items: [apiDir('/foo')]});
              } else if (path === '/foo') {
                return of({items: [apiDir('/foo/bar')]});
              } else if (path === '/foo/bar') {
                return of({items: [apiDir('/foo/bar/baz')]});
              } else {
                throw new Error();
              }
            });

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo/bar');

    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/foo');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/foo/bar');

    const results = await firstValueFrom(vfsViewLocalStore.directoryTree$);

    expect(results).toEqual(jasmine.objectContaining({
      path: '/',
      children: [jasmine.objectContaining({
        path: '/foo',
        children: [jasmine.objectContaining({
          path: '/foo/bar',
          children: [jasmine.objectContaining({path: '/foo/bar/baz'})],
        })],
      })],
    }));
  });

  it('navigateToPath lists files from NTFS, TSK, AND OS', async () => {
    const listFiles: HttpApiService['listFiles'] = (clientId, pathType, path) =>
        of({items: [apiFile(`/${pathType}file`, pathType)]});
    httpApiService.listFiles =
        jasmine.createSpy('listFiles').and.callFake(listFiles);

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    expect(httpApiService.listFiles).toHaveBeenCalledTimes(3);
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.TSK, '/');
    expect(httpApiService.listFiles)
        .toHaveBeenCalledWith('C.1234', PathSpecPathType.NTFS, '/');

    const tree = await firstValueFrom(vfsViewLocalStore.currentDirectory$);
    expect(tree).toEqual(
        jasmine.objectContaining({
          path: '/',
          children: [
            jasmine.objectContaining({path: '/OSfile'}),
            jasmine.objectContaining({path: '/TSKfile'}),
            jasmine.objectContaining({path: '/NTFSfile'}),
          ]
        }),
    );
  });

  it('navigateToPath merges files that appear in multiple PathSpecs',
     async () => {
       const listFiles: HttpApiService['listFiles'] =
           (clientId, pathType, path) => {
             if (pathType === PathSpecPathType.OS) {
               return of({items: [{...apiFile(`/file`, pathType), age: 1}]});
             } else if (pathType === PathSpecPathType.TSK) {
               return of({items: [{...apiFile(`/file`, pathType), age: 2}]});
             } else if (pathType === PathSpecPathType.NTFS) {
               return of({items: [{...apiFile(`/file`, pathType), age: 3}]});
             } else {
               throw new Error('unknown pathspec');
             }
           };

       httpApiService.listFiles =
           jasmine.createSpy('listFiles').and.callFake(listFiles);

       vfsViewLocalStore.resetClientId('C.1234');
       vfsViewLocalStore.navigateToPath('/');

       expect(httpApiService.listFiles).toHaveBeenCalledTimes(3);
       expect(httpApiService.listFiles)
           .toHaveBeenCalledWith('C.1234', PathSpecPathType.OS, '/');
       expect(httpApiService.listFiles)
           .toHaveBeenCalledWith('C.1234', PathSpecPathType.TSK, '/');
       expect(httpApiService.listFiles)
           .toHaveBeenCalledWith('C.1234', PathSpecPathType.NTFS, '/');

       const tree = await firstValueFrom(vfsViewLocalStore.currentDirectory$);
       expect(tree).toEqual(
           jasmine.objectContaining({
             path: '/',
             children: [
               jasmine.objectContaining(
                   {path: '/file', pathtype: PathSpecPathType.NTFS}),
             ]
           }),
       );
     });

  it('directory loading is indicated in loading boolean', async () => {
    const root$ = new Subject<ApiListFilesResult>();
    const sub$ = new Subject<ApiListFilesResult>();

    httpApiService.listFiles = jasmine.createSpy('listFiles')
                                   .and.callFake((clientId, pathType, path) => {
                                     if (pathType !== PathSpecPathType.OS) {
                                       return of({});
                                     } else if (path === '/') {
                                       return root$;
                                     } else if (path === '/foo') {
                                       return sub$;
                                     } else {
                                       throw new Error();
                                     }
                                   });

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo');

    expect(await firstValueFrom(vfsViewLocalStore.directoryTree$))
        .toEqual(jasmine.objectContaining({
          path: '/',
          loading: true,
        }));

    root$.next({items: [apiDir('/foo')]});
    root$.complete();

    expect(await firstValueFrom(vfsViewLocalStore.directoryTree$))
        .toEqual(jasmine.objectContaining({
          path: '/',
          loading: false,
          children: [jasmine.objectContaining({
            path: '/foo',
            loading: true,
          })],
        }));

    sub$.next({items: [apiDir('/foo/bar')]});
    sub$.complete();

    expect(await firstValueFrom(vfsViewLocalStore.directoryTree$))
        .toEqual(jasmine.objectContaining({
          path: '/',
          loading: false,
          children: [jasmine.objectContaining({
            path: '/foo',
            loading: false,
          })],
        }));
  });

  it('listCurrentDirectory calls refreshVfsFolder', async () => {
    expect(httpApiService.refreshVfsFolder).not.toHaveBeenCalled();

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    httpApiService.mockedObservables.listFiles.next({items: [apiDir('/foo')]});

    vfsViewLocalStore.listCurrentDirectory();

    expect(httpApiService.refreshVfsFolder)
        .toHaveBeenCalledOnceWith(
            'C.1234', PathSpecPathType.OS, '/', undefined);

    httpApiService.mockedObservables.refreshVfsFolder.next(
        {items: [apiDir('/bar')]});

    const results = await firstValueFrom(vfsViewLocalStore.directoryTree$);
    expect(results).toEqual(
        jasmine.objectContaining({
          path: '/',
          children: [jasmine.objectContaining({path: '/bar'})],
        }),
    );
  });

  it('deep listCurrentDirectory refreshes expanded sub-directories',
     async () => {
       expect(httpApiService.refreshVfsFolder).not.toHaveBeenCalled();

       vfsViewLocalStore.resetClientId('C.1234');
       vfsViewLocalStore.navigateToPath('/');

       httpApiService.listFiles =
           jasmine.createSpy('listFiles')
               .and.callFake((clientId, pathType, path) => {
                 if (path === '/') {
                   return of({
                     items: [
                       apiDir('/foo'),
                       apiDir('/neverexpanded'),
                       apiDir('/collapsed'),
                     ]
                   });
                 } else if (path === '/foo') {
                   return of({items: [apiDir('/foo/bar')]});
                 } else if (path === '/collapsed') {
                   return of({items: [apiDir('/collapsed/sub')]});
                 } else {
                   throw new Error(path);
                 }
               });

       vfsViewLocalStore.expandDirectories(['/', '/foo', '/collapsed']);

       vfsViewLocalStore.collapseDirectories(['/collapsed']);

       vfsViewLocalStore.listCurrentDirectory({maxDepth: 5});

       expect(httpApiService.refreshVfsFolder)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/', {maxDepth: 5});

       httpApiService.listFiles =
           jasmine.createSpy('listFiles')
               .and.callFake((clientId, pathType, path) => {
                 if (path === '/foo') {
                   return of({
                     items: [
                       apiDir('/foo/newbar'),
                     ]
                   });
                 } else {
                   // Raise if listFiles would've been called for / again --
                   // results for / should come from refreshVfsFolder call.
                   throw new Error(path);
                 }
               });

       httpApiService.mockedObservables.refreshVfsFolder.next({
         items: [
           apiDir('/foo'),
           apiDir('/newfoo'),
           apiDir('/neverexpanded'),
           apiDir('/collapsed'),
         ]
       });

       const results = await firstValueFrom(vfsViewLocalStore.directoryTree$);
       expect(results).toEqual(
           jasmine.objectContaining({
             path: '/',
             children: [
               jasmine.objectContaining({
                 path: '/foo',
                 children: [jasmine.objectContaining({path: '/foo/newbar'})],
               }),
               jasmine.objectContaining({path: '/newfoo'}),
               jasmine.objectContaining({path: '/neverexpanded'}),
               jasmine.objectContaining({path: '/collapsed'}),
             ],
           }),
       );
     });

  it('listCurrentDirectory updates isListingCurrentDirectory$', async () => {
    expect(await firstValueFrom(vfsViewLocalStore.isListingCurrentDirectory$))
        .toBeFalse();

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    expect(await firstValueFrom(vfsViewLocalStore.isListingCurrentDirectory$))
        .toBeFalse();

    vfsViewLocalStore.listCurrentDirectory();

    expect(await firstValueFrom(vfsViewLocalStore.isListingCurrentDirectory$))
        .toBeTrue();

    httpApiService.mockedObservables.refreshVfsFolder.next(
        {items: [apiDir('/bar')]});

    expect(await firstValueFrom(vfsViewLocalStore.isListingCurrentDirectory$))
        .toBeFalse();
  });

  it('currentDirectory$ emits current directory with children', async () => {
    httpApiService.listFiles = jasmine.createSpy('listFiles')
                                   .and.callFake((clientId, pathType, path) => {
                                     if (path === '/') {
                                       return of({items: [apiDir('/foo')]});
                                     } else if (path === '/foo') {
                                       return of({
                                         items: [
                                           apiDir('/foo/bar'),
                                           apiDir('/foo/baz'),
                                         ]
                                       });
                                     } else {
                                       throw new Error();
                                     }
                                   });

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo');

    const results = await firstValueFrom(vfsViewLocalStore.currentDirectory$);

    expect(results).toEqual(jasmine.objectContaining({
      path: '/foo',
      children: [
        jasmine.objectContaining({path: '/foo/bar'}),
        jasmine.objectContaining({path: '/foo/baz'}),
      ],
    }));
  });

  it('currentDirectory$ emits parent directory if file is selected',
     async () => {
       httpApiService.listFiles =
           jasmine.createSpy('listFiles')
               .and.callFake((clientId, pathType, path) => {
                 if (path === '/' && pathType === PathSpecPathType.OS) {
                   return of({items: [apiDir('/foo')]});
                 } else if (
                     path === '/foo' && pathType === PathSpecPathType.OS) {
                   return of({
                     items: [
                       apiFile('/foo/barfile'),
                       apiDir('/foo/baz'),
                     ]
                   });
                 } else {
                   return of({});
                 }
               });

       vfsViewLocalStore.resetClientId('C.1234');
       vfsViewLocalStore.navigateToPath('/foo/barfile');

       const results =
           await firstValueFrom(vfsViewLocalStore.currentDirectory$);

       expect(results).toEqual(jasmine.objectContaining({
         path: '/foo',
         children: [
           jasmine.objectContaining({path: '/foo/barfile'}),
           jasmine.objectContaining({path: '/foo/baz'}),
         ],
       }));
     });
});
