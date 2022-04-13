import {Location} from '@angular/common';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newFile, newPathSpec} from '../../lib/models/model_test_util';
import {PathSpecPathType} from '../../lib/models/vfs';
import {FileDetailsLocalStore} from '../../store/file_details_local_store';
import {mockFileDetailsLocalStore} from '../../store/file_details_local_store_test_util';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {VfsViewLocalStore} from '../../store/vfs_view_local_store';
import {mockVfsViewLocalStore} from '../../store/vfs_view_local_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';
import {ClientDetailsModule} from '../client_details/module';
import {FileDetails} from '../file_details/file_details';

import {ClientPageModule} from './client_page_module';
import {CLIENT_PAGE_ROUTES} from './routing';
import {VfsSection} from './vfs_section';


initTestEnvironment();

describe('VfsSection', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            RouterTestingModule.withRoutes(CLIENT_PAGE_ROUTES),
            ApiModule,
            NoopAnimationsModule,
            ClientPageModule,
            ClientDetailsModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            VfsViewLocalStore, {useFactory: mockVfsViewLocalStore})
        .overrideProvider(
            FileDetailsLocalStore, {useFactory: mockFileDetailsLocalStore})
        .compileComponents();
  }));

  it('shows tree view with directory listing', async () => {
    await TestBed.inject(Router).navigate(
        ['clients', 'C.1234', 'files', '/topdir']);
    const fixture = TestBed.createComponent(VfsSection);
    fixture.detectChanges();

    const vfsViewLocalStore =
        injectMockStore(VfsViewLocalStore, fixture.debugElement);
    vfsViewLocalStore.mockedObservables.directoryTree$.next({
      path: '/',
      pathtype: PathSpecPathType.OS,
      isDirectory: true,
      name: '/',
      loading: false,
      children: [{
        path: '/topdir',
        pathtype: PathSpecPathType.OS,
        isDirectory: true,
        name: 'topdir',
        loading: false,
        children: [{
          path: '/topdir/subdir',
          pathtype: PathSpecPathType.OS,
          isDirectory: true,
          name: 'subdir',
          loading: false,
        }],
      }]

    });
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent).toContain('topdir');
    expect(fixture.debugElement.nativeElement.textContent).toContain('subdir');

    const links = fixture.debugElement.queryAll(By.css('a.directory-link'));
    const urls = links.map(link => link.attributes['href']);
    expect(urls.length).toEqual(3);
    expect(urls[0]).toMatch(/.*%2F$/);
    expect(urls[1]).toMatch(/.*%2Ftopdir$/);
    expect(urls[2]).toMatch(/.*%2Ftopdir%2Fsubdir$/);
  });

  it('shows file details of the selected file', async () => {
    await TestBed.inject(Router).navigate(
        ['clients', 'C.1234', 'files', '/topdir']);
    const fixture = TestBed.createComponent(VfsSection);
    fixture.detectChanges();

    const selectedClientGlobalStore =
        injectMockStore(SelectedClientGlobalStore);
    selectedClientGlobalStore.mockedObservables.clientId$.next('C.1234');
    const vfsViewLocalStore =
        injectMockStore(VfsViewLocalStore, fixture.debugElement);
    vfsViewLocalStore.mockedObservables.currentFile$.next(newFile({
      path: '/foo/bar',
      pathtype: PathSpecPathType.OS,
      isDirectory: false,
      name: 'bar',
    }));
    fixture.detectChanges();

    const fileDetails = fixture.debugElement.query(By.directive(FileDetails));
    expect(fileDetails).not.toBeNull();
  });


  it('shows table with directory contents', async () => {
    await TestBed.inject(Router).navigate(
        ['clients', 'C.1234', 'files', '/topdir']);
    const fixture = TestBed.createComponent(VfsSection);
    fixture.detectChanges();

    const vfsViewLocalStore =
        injectMockStore(VfsViewLocalStore, fixture.debugElement);
    vfsViewLocalStore.mockedObservables.currentDirectory$.next({
      path: '/',
      pathtype: PathSpecPathType.OS,
      isDirectory: true,
      name: '/',
      children: [
        {
          path: '/topdir',
          pathtype: PathSpecPathType.OS,
          isDirectory: true,
          name: 'topdir',
        },
        newFile({
          path: '/anotherfile',
          pathtype: PathSpecPathType.OS,
          isDirectory: false,
          name: 'anotherfile',
          stat: {
            pathspec: newPathSpec({path: '/anotherfile'}),
          },
        }),
      ]

    });
    fixture.detectChanges();

    const directoryTable =
        fixture.debugElement.query(By.css('.directory-table'));
    expect(directoryTable.nativeElement.textContent).toContain('topdir');
    expect(directoryTable.nativeElement.textContent).toContain('anotherfile');
  });

  it('clicking on table row navigates to path', fakeAsync(async () => {
       await TestBed.inject(Router).navigate(
           ['clients', 'C.1234', 'files', '/topdir']);

       const location: Location = TestBed.inject(Location);
       const fixture = TestBed.createComponent(VfsSection);
       fixture.detectChanges();

       const vfsViewLocalStore =
           injectMockStore(VfsViewLocalStore, fixture.debugElement);
       vfsViewLocalStore.mockedObservables.currentDirectory$.next({
         path: '/topdir',
         pathtype: PathSpecPathType.OS,
         isDirectory: true,
         name: 'topdir',
         children: [
           {
             path: '/topdir/folder',
             pathtype: PathSpecPathType.OS,
             isDirectory: true,
             name: 'folder',
           },
           newFile({
             path: '/topdir/anotherfile',
             pathtype: PathSpecPathType.OS,
             isDirectory: false,
             name: 'anotherfile',
             stat: {
               pathspec: newPathSpec({path: '/topdir/anotherfile'}),
             },
           }),
         ]

       });
       fixture.detectChanges();

       expect(location.path()).toMatch(/.*%2Ftopdir\/stat$/);

       const rows =
           fixture.debugElement.queryAll(By.css('.directory-table tbody tr'));
       expect(rows.length).toEqual(2);
       rows[1].triggerEventHandler('click', new MouseEvent('click'));

       fixture.detectChanges();
       tick();  // after tick(), URL changes will have taken into effect.

       // Testing nested child-routes is really hard to get right - we don't
       // assert the exact path, because it evaluates to /clients/<path> which
       // redirects to /clients/<path>/flows. In prod, everything works though,
       // so we simply assert that the final string contains the linked path.
       expect(location.path()).toContain('%2Ftopdir%2Fanotherfile');
     }));
});
