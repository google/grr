import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {PathSpecPathType} from '../../lib/api/api_interfaces';
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
    fixture.detectChanges();

    selectedClientGlobalStore.mockedObservables.clientId$.next('C.8765');
    fixture.detectChanges();

    expect(fileDetailsLocalStore.selectFile).toHaveBeenCalledWith({
      clientId: 'C.8765',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar/baz',
    });
    expect(fileDetailsLocalStore.fetchContent).toHaveBeenCalled();
  });

  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(FileDetails);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next(
        'hello file content');
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('hello file content');
  });
});
