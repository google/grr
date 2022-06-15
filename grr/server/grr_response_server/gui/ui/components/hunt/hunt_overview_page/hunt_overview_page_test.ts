import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {injectMockStore, mockHuntOverviewPageLocalStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {HuntOverviewPage} from './hunt_overview_page';

initTestEnvironment();

describe('app-hunt-overview-page', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RouterTestingModule,
            HuntOverviewPage,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntOverviewPageLocalStore,
            {useFactory: mockHuntOverviewPageLocalStore})
        .compileComponents();
  }));

  it('displays hunt information', async () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);

    expect(huntPageLocalStore.setArgs).toHaveBeenCalled();

    huntPageLocalStore.mockedObservables.results$.next(
        [{huntId: '123', description: 'Collect foobar'}]);
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('Collect foobar');
  });
});
