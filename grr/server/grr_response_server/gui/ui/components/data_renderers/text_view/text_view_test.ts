import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ContentFetchMode, FileDetailsLocalStore} from '../../../store/file_details_local_store';
import {FileDetailsLocalStoreMock, mockFileDetailsLocalStore} from '../../../store/file_details_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {TextView} from './text_view';
import {TextViewModule} from './text_view_module';

initTestEnvironment();

describe('TextView Component', () => {
  let fileDetailsLocalStore: FileDetailsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    fileDetailsLocalStore = mockFileDetailsLocalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            TextViewModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FileDetailsLocalStore, {useFactory: () => fileDetailsLocalStore})
        .compileComponents();
  }));

  it('triggers loading content', () => {
    const fixture = TestBed.createComponent(TextView);
    fixture.detectChanges();

    expect(fileDetailsLocalStore.setMode)
        .toHaveBeenCalledOnceWith(ContentFetchMode.TEXT);
    expect(fileDetailsLocalStore.fetchMoreContent)
        .toHaveBeenCalledOnceWith(FileDetailsLocalStore.DEFAULT_PAGE_SIZE);
  });


  it('shows loaded content', () => {
    const fixture = TestBed.createComponent(TextView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next(
        'hello file content');
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('hello file content');
  });

  it('indicates that more content is available', () => {
    const fixture = TestBed.createComponent(TextView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeTruthy();
  });

  it('hides more content indicators when full content has been loaded', () => {
    const fixture = TestBed.createComponent(TextView);
    fixture.detectChanges();

    fileDetailsLocalStore.mockedObservables.textContent$.next('hello');
    fileDetailsLocalStore.mockedObservables.hasMore$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeTruthy();

    fileDetailsLocalStore.mockedObservables.hasMore$.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.more-indicator'))).toBeFalsy();
  });
});
