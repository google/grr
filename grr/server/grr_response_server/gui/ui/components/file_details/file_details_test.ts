import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {PathSpecPathType} from '../../lib/api/api_interfaces';
import {Writable} from '../../lib/type_utils';
import {FileDetailsLocalStore} from '../../store/file_details_local_store';
import {FileDetailsLocalStoreMock, mockFileDetailsLocalStore} from '../../store/file_details_local_store_test_util';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {mockSelectedClientGlobalStore, SelectedClientGlobalStoreMock} from '../../store/selected_client_global_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';

import {FileDetails} from './file_details';
import {FileDetailsModule} from './file_details_module';

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

  it('queries file content on route change', () => {
    const fixture = TestBed.createComponent(FileDetails);
    (fixture.componentInstance as Writable<FileDetails>).DEFAULT_PAGE_LENGTH =
        BigInt(123);
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

  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.details$.next(
        {stat: {pathspec: {path: '/examplefile'}}});
    fileDetailsLocalStore.mockedObservables.textContent$.next(
        'hello file content');
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('/examplefile');
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('hello file content');
  });

  it('indicates that more content is available', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeTruthy();
    expect(fixture.debugElement.query(By.css('.load-more'))).toBeTruthy();
  });

  it('hides more content indicators when full content has been loaded', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeTruthy();
    expect(fixture.debugElement.query(By.css('.load-more'))).toBeTruthy();

    fileDetailsLocalStore.mockedObservables.hasMore$.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeFalsy();
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

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fixture.detectChanges();

    expect(fileDetailsLocalStore.recollectFile).not.toHaveBeenCalled();

    const recollectButton = fixture.debugElement.query(By.css('.recollect'));
    recollectButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(fileDetailsLocalStore.recollectFile).toHaveBeenCalledOnceWith();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hellonew');
    fixture.detectChanges();
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('hellonew');
  });
});
