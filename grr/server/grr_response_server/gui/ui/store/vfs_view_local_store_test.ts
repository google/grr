import {TestBed} from '@angular/core/testing';
import {firstValueFrom, of, Subject} from 'rxjs';

import {ApiBrowseFilesystemResult, ApiFile, PathSpecPathType} from '../lib/api/api_interfaces';
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
          age: '123',
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
    const browseFilesystem: HttpApiService['browseFilesystem'] =
        (clientId, path) =>
            of({items: [{path: '/', children: [apiDir('/foo')]}]});
    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake(browseFilesystem);

    expect(httpApiService.browseFilesystem).not.toHaveBeenCalled();

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    expect(httpApiService.browseFilesystem)
        .toHaveBeenCalledOnceWith('C.1234', '/', {includeDirectoryTree: true});

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
    expect(httpApiService.browseFilesystem).not.toHaveBeenCalled();

    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake(() => {
          return of({
            items: [
              {path: '/', children: [apiDir('/foo')]},
              {path: '/foo', children: [apiDir('/foo/bar')]},
              {path: '/foo/bar', children: [apiDir('/foo/bar/baz')]},
            ],
          });
        });

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo/bar');

    expect(httpApiService.browseFilesystem)
        .toHaveBeenCalledOnceWith(
            'C.1234', '/foo/bar', {includeDirectoryTree: true});

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
    const browseFilesystem: HttpApiService['browseFilesystem'] =
        (clientId, path) => of({
          items: [
            {
              path: '/',
              children: [
                apiFile(`/OSfile`),
                apiFile(`/TSKfile`, PathSpecPathType.TSK),
              ],
            },
          ]
        });
    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake(browseFilesystem);

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/');

    expect(httpApiService.browseFilesystem)
        .toHaveBeenCalledOnceWith('C.1234', '/', {includeDirectoryTree: true});

    const tree = await firstValueFrom(vfsViewLocalStore.currentDirectory$);
    expect(tree).toEqual(
        jasmine.objectContaining({
          path: '/',
          children: [
            jasmine.objectContaining({path: '/OSfile'}),
            jasmine.objectContaining({path: '/TSKfile'}),
          ]
        }),
    );
  });

  it('directory loading is indicated in loading boolean', async () => {
    const root$ = new Subject<ApiBrowseFilesystemResult>();

    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake(() => root$);

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo');

    expect(await firstValueFrom(vfsViewLocalStore.directoryTree$))
        .toEqual(jasmine.objectContaining({
          path: '/',
          loading: true,
        }));

    root$.next({
      items: [
        {path: '/', children: [apiDir('/foo')]},
        {path: '/foo', children: [apiDir('/foo/bar')]},
        {path: '/foo/bar', children: [apiDir('/foo/bar/baz')]},
      ],
    });
    root$.complete();

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

    httpApiService.mockedObservables.browseFilesystem.next(
        {items: [{path: '/', children: [apiDir('/foo')]}]});

    vfsViewLocalStore.listCurrentDirectory();

    expect(httpApiService.refreshVfsFolder)
        .toHaveBeenCalledOnceWith(
            'C.1234', PathSpecPathType.OS, '/', undefined);

    httpApiService.mockedObservables.refreshVfsFolder.next(
        {items: [{path: '/', children: [apiDir('/bar')]}]});

    const results = await firstValueFrom(vfsViewLocalStore.directoryTree$);
    expect(results).toEqual(
        jasmine.objectContaining({
          path: '/',
          children: [jasmine.objectContaining({path: '/bar'})],
        }),
    );
  });

  it('listCurrentDirectory calls refresh for directory name', async () => {
    expect(httpApiService.refreshVfsFolder).not.toHaveBeenCalled();

    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake((clientId, path) => {
          if (path === '/foo/bar') {
            return of({
              items: [
                {path: '/', children: [apiDir('/foo')]},
                {path: '/foo', children: [apiFile('/foo/bar')]},
              ],
            });
          } else {
            throw new Error(path);
          }
        });

    vfsViewLocalStore.resetClientId('C.1234');
    vfsViewLocalStore.navigateToPath('/foo/bar');
    vfsViewLocalStore.listCurrentDirectory();

    expect(httpApiService.refreshVfsFolder)
        .toHaveBeenCalledOnceWith(
            'C.1234', PathSpecPathType.OS, '/foo', undefined);
  });

  it('deep listCurrentDirectory refreshes expanded sub-directories',
     async () => {
       expect(httpApiService.refreshVfsFolder).not.toHaveBeenCalled();

       httpApiService.browseFilesystem =
           jasmine.createSpy('browseFilesystem')
               .and.callFake((clientId, path) => {
                 if (path === '/') {
                   return of({
                     items: [{
                       path: '/',
                       children: [
                         apiDir('/foo'),
                         apiDir('/neverexpanded'),
                         apiDir('/collapsed'),
                       ]
                     }],
                   });
                 } else if (path === '/foo') {
                   return of({
                     items: [{path: '/foo', children: [apiDir('/foo/bar')]}]
                   });
                 } else if (path === '/collapsed') {
                   return of({
                     items: [{
                       path: '/collapsed',
                       children: [apiDir('/collapsed/sub')]
                     }]
                   });
                 } else {
                   throw new Error(path);
                 }
               });

       vfsViewLocalStore.resetClientId('C.1234');
       vfsViewLocalStore.navigateToPath('/');

       expect(httpApiService.browseFilesystem)
           .toHaveBeenCalledOnceWith(
               'C.1234', '/', {includeDirectoryTree: true});

       vfsViewLocalStore.expandDirectories(['/', '/foo', '/collapsed']);

       expect(httpApiService.browseFilesystem)
           .toHaveBeenCalledWith(
               'C.1234', '/foo', {includeDirectoryTree: false});
       expect(httpApiService.browseFilesystem)
           .toHaveBeenCalledWith(
               'C.1234', '/collapsed', {includeDirectoryTree: false});

       vfsViewLocalStore.collapseDirectories(['/collapsed']);

       vfsViewLocalStore.listCurrentDirectory({maxDepth: 5});

       expect(httpApiService.refreshVfsFolder)
           .toHaveBeenCalledOnceWith(
               'C.1234', PathSpecPathType.OS, '/', {maxDepth: '5'});

       httpApiService.browseFilesystem = jasmine.createSpy('browseFilesystem')
                                             .and.callFake((clientId, path) => {
                                               if (path === '/foo') {
                                                 return of({
                                                   items: [{
                                                     path: '/foo',
                                                     children: [
                                                       apiDir('/foo/newbar'),
                                                     ]
                                                   }]
                                                 });
                                               } else {
                                                 // Raise if browseFilesystem
                                                 // would've been called for /
                                                 // again
                                                 // -- results for / should come
                                                 // from refreshVfsFolder call.
                                                 throw new Error(path);
                                               }
                                             });

       httpApiService.mockedObservables.refreshVfsFolder.next({
         items: [{
           path: '/',
           children: [
             apiDir('/foo'),
             apiDir('/newfoo'),
             apiDir('/neverexpanded'),
             apiDir('/collapsed'),
           ]
         }]
       });

       expect(httpApiService.browseFilesystem)
           .toHaveBeenCalledOnceWith(
               'C.1234', '/foo', {includeDirectoryTree: false});

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
    httpApiService.browseFilesystem =
        jasmine.createSpy('browseFilesystem').and.callFake((clientId, path) => {
          if (path === '/foo') {
            return of({
              items: [
                {
                  path: '/',
                  children: [apiDir('/foo')],
                },
                {
                  path: '/foo',
                  children: [
                    apiDir('/foo/bar'),
                    apiDir('/foo/baz'),
                  ],
                },
              ],
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
       httpApiService.browseFilesystem =
           jasmine.createSpy('browseFilesystem')
               .and.callFake((clientId, path) => {
                 if (path === '/foo/barfile') {
                   return of({
                     items: [
                       {
                         path: '/',
                         children: [apiDir('/foo')],
                       },
                       {
                         path: '/foo',
                         children: [
                           apiFile('/foo/barfile'),
                           apiDir('/foo/baz'),
                         ],
                       },
                     ],
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
