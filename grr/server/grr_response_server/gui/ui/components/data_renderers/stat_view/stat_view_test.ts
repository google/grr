import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {PathSpecPathType} from '../../../lib/api/api_interfaces';
import {FileDetailsLocalStore} from '../../../store/file_details_local_store';
import {FileDetailsLocalStoreMock, mockFileDetailsLocalStore} from '../../../store/file_details_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {StatView} from './stat_view';
import {StatViewModule} from './stat_view_module';

initTestEnvironment();

describe('StatView Component', () => {
  let fileDetailsLocalStore: FileDetailsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    fileDetailsLocalStore = mockFileDetailsLocalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            StatViewModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FileDetailsLocalStore, {useFactory: () => fileDetailsLocalStore})
        .compileComponents();
  }));

  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(StatView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.details$.next({
      name: 'examplefile',
      isDirectory: false,
      path: 'fs/os/examplefile',
      pathtype: PathSpecPathType.OS,
      lastMetadataCollected: new Date(1),
      hash: {
        sha256: '123abc',
      },
      stat: {
        pathspec: {
          path: '/examplefile',
          pathtype: PathSpecPathType.OS,
          segments: [{
            path: '/examplefile',
            pathtype: PathSpecPathType.OS,
          }],
        }
      },
    });
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('/examplefile');
    expect(fixture.debugElement.nativeElement.textContent).toContain('123abc');
  });

  it('shows nested pathspecs', () => {
    const fixture = TestBed.createComponent(StatView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.details$.next({
      name: 'examplefile',
      isDirectory: false,
      path: 'fs/ntfs/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}' +
          '/examplefile',
      pathtype: PathSpecPathType.OS,
      lastMetadataCollected: new Date(1),
      stat: {
        pathspec: {
          path:
              '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}/examplefile',
          pathtype: PathSpecPathType.NTFS,
          segments: [
            {
              path: '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}',
              pathtype: PathSpecPathType.OS,
            },
            {
              path: '/examplefile',
              pathtype: PathSpecPathType.NTFS,
            },
          ],
        }
      },
    });
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain(
            '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}' +
            'NTFS' +
            '/examplefile');
  });
});
