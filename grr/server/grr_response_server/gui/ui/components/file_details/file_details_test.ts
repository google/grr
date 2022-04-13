import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {PathSpecPathType} from '../../lib/api/api_interfaces';
import {getFileBlobUrl} from '../../lib/api/http_api_service';
import {newFile, newPathSpec} from '../../lib/models/model_test_util';
import {Writable} from '../../lib/type_utils';
import {FileDetailsLocalStore} from '../../store/file_details_local_store';
import {FileDetailsLocalStoreMock, mockFileDetailsLocalStore} from '../../store/file_details_local_store_test_util';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {mockSelectedClientGlobalStore, SelectedClientGlobalStoreMock} from '../../store/selected_client_global_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';

import {FileDetails} from './file_details';
import {FileDetailsModule} from './file_details_module';
import {FileDetailsPage} from './file_details_page';
import {FILE_DETAILS_ROUTES} from './routing';

initTestEnvironment();

describe('FileDetails Component', () => {
  let fileDetailsLocalStore: FileDetailsLocalStoreMock;
  let selectedClientGlobalStore: SelectedClientGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    fileDetailsLocalStore = mockFileDetailsLocalStore();
    selectedClientGlobalStore = mockSelectedClientGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FileDetailsModule,
            RouterTestingModule.withRoutes(FILE_DETAILS_ROUTES),
          ],
          providers: [
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
            {
              provide: SelectedClientGlobalStore,
              useFactory: () => selectedClientGlobalStore,
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FileDetailsLocalStore, {useFactory: () => fileDetailsLocalStore})
        .compileComponents();

    TestBed.inject(Router).navigate(
        [{outlets: {drawer: ['files', 'os', '/foo/bar/baz']}}]);
  }));

  it('should be created', () => {
    const fixture = TestBed.createComponent(FileDetails);
    expect(fixture).toBeTruthy();
  });

  it('queries file content on route change through FileDetailsPage', () => {
    const fixture = TestBed.createComponent(FileDetailsPage);

    const fileDetails = fixture.debugElement.query(By.directive(FileDetails));
    (fileDetails.componentInstance as Writable<FileDetails>)
        .DEFAULT_PAGE_LENGTH = BigInt(123);
    fixture.detectChanges();

    selectedClientGlobalStore.mockedObservables.clientId$.next('C.8765');
    fixture.detectChanges();

    expect(fileDetailsLocalStore.selectFile).toHaveBeenCalledWith({
      clientId: 'C.8765',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar/baz',
    });
    expect(fileDetailsLocalStore.fetchDetails).toHaveBeenCalled();
    expect(fileDetailsLocalStore.fetchMoreContent)
        .toHaveBeenCalledOnceWith(BigInt(123));
  });

  it('queries file content on input change', () => {
    const fixture = TestBed.createComponent(FileDetails);

    (fixture.componentInstance as Writable<FileDetails>).DEFAULT_PAGE_LENGTH =
        BigInt(123);
    fixture.detectChanges();

    fixture.componentInstance.file = {
      clientId: 'C.8765',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar/baz'
    };
    fixture.detectChanges();

    expect(fileDetailsLocalStore.selectFile).toHaveBeenCalledWith({
      clientId: 'C.8765',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar/baz',
    });
    expect(fileDetailsLocalStore.fetchDetails).toHaveBeenCalled();
    expect(fileDetailsLocalStore.fetchMoreContent)
        .toHaveBeenCalledOnceWith(BigInt(123));
  });

  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.file$.next({
      clientId: 'C.1234',
      path: '/examplefile',
      pathType: PathSpecPathType.OS,
    });
    fileDetailsLocalStore.mockedObservables.details$.next(newFile({
      name: 'examplefile',
      isDirectory: false,
      path: 'fs/os/examplefile',
      pathtype: PathSpecPathType.OS,
      stat: {pathspec: newPathSpec({path: '/examplefile'})},
    }));
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('examplefile');
  });

  it('indicates that more content is available', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.load-more'))).toBeTruthy();
  });

  it('hides more content indicators when full content has been loaded', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.load-more'))).toBeTruthy();

    fileDetailsLocalStore.mockedObservables.hasMore$.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.load-more'))).toBeFalsy();
  });

  it('queries more file content on "load more" click', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    const previousCalls = fileDetailsLocalStore.fetchMoreContent.calls.count();
    const loadMoreButton = fixture.debugElement.query(By.css('.load-more'));
    loadMoreButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fileDetailsLocalStore.fetchMoreContent)
        .toHaveBeenCalledTimes(previousCalls + 1);
  });

  it('reloads content on "recollect" click', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.file$.next(
        {clientId: 'C.1', pathType: PathSpecPathType.OS, path: '/examplefile'});
    fileDetailsLocalStore.mockedObservables.details$.next(newFile({
      name: 'examplefile',
      isDirectory: false,
      path: 'fs/os/examplefile',
      pathtype: PathSpecPathType.OS,
      stat: {pathspec: newPathSpec({path: '/examplefile'})},
    }));
    fixture.detectChanges();

    expect(fileDetailsLocalStore.recollectFile).not.toHaveBeenCalled();

    const recollectButton = fixture.debugElement.query(By.css('.recollect'));
    recollectButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fileDetailsLocalStore.recollectFile).toHaveBeenCalledOnceWith();

    fileDetailsLocalStore.mockedObservables.details$.next(newFile({
      name: 'EXAMPLEFILE',
      path: 'fs/os/EXAMPLEFILE',
      pathtype: PathSpecPathType.OS,
      stat: {pathspec: newPathSpec({path: '/EXAMPLEFILE'})},
    }));

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('EXAMPLEFILE');
  });

  it('shows download button', async () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.file$.next(
        {clientId: 'C.1', pathType: PathSpecPathType.OS, path: '/foo/bar'});
    fileDetailsLocalStore.mockedObservables.details$.next(newFile({
      name: 'bar',
      path: 'fs/os/foo/bar',
      pathtype: PathSpecPathType.OS,
      stat: {pathspec: newPathSpec({path: '/foo/bar'})},
    }));
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('a[download]'));
    expect(button.attributes['download']).toEqual('bar');
    expect(button.attributes['href'])
        .toEqual(getFileBlobUrl('C.1', PathSpecPathType.OS, '/foo/bar'));
  });
});
