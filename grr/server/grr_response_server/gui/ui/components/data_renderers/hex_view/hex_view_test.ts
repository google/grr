import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {arrayBufferOf} from '../../../lib/type_utils';
import {ContentFetchMode, FileDetailsLocalStore} from '../../../store/file_details_local_store';
import {FileDetailsLocalStoreMock, mockFileDetailsLocalStore} from '../../../store/file_details_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {HexView} from './hex_view';
import {HexViewModule} from './hex_view_module';

initTestEnvironment();

describe('HexView Component', () => {
  let fileDetailsLocalStore: FileDetailsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    fileDetailsLocalStore = mockFileDetailsLocalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HexViewModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FileDetailsLocalStore, {useFactory: () => fileDetailsLocalStore})
        .compileComponents();
  }));

  it('triggers loading content', () => {
    const fixture = TestBed.createComponent(HexView);
    fixture.detectChanges();

    expect(fileDetailsLocalStore.setMode)
        .toHaveBeenCalledOnceWith(ContentFetchMode.BLOB);
    expect(fileDetailsLocalStore.fetchMoreContent)
        .toHaveBeenCalledOnceWith(FileDetailsLocalStore.DEFAULT_PAGE_SIZE);
  });

  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(HexView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.blobContent$.next(arrayBufferOf([
      0x67, 0x6E, 0x6F, 0x6D, 0x65, 0x2D, 0x73, 0x63,
      0x72, 0x65, 0x65, 0x6E, 0x73, 0x68, 0x6F, 0x74,

      0x50, 0x4E, 0x47,
    ]));
    fixture.detectChanges();

    const strippedText =
        fixture.debugElement.nativeElement.textContent.replace(/\s+/g, '');

    expect(strippedText).toContain('0123456789ABCDEF');  // Header offsets.
    expect(strippedText).toContain('000000');            // Line offsets.
    expect(strippedText).toContain('000010');            // Line offsets.
    expect(strippedText)
        .toContain(
            '676E6F6D652D73637265656E73686F74');  // Hex content on line 1.
    expect(strippedText).toContain('504E47');     // Hex content on line 2.
    expect(strippedText)
        .toContain('gnome-screenshot');     // Text content on line 1.
    expect(strippedText).toContain('PNG');  // Text content on line 2.
  });
});
