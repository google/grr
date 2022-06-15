import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {HuntPageLocalStore} from '../../../store/hunt_page_local_store';
import {mockHuntPageLocalStore} from '../../../store/hunt_page_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {HuntPage} from './hunt_page';
import {HuntPageModule} from './module';
import {HUNT_PAGE_ROUTES} from './routing';

initTestEnvironment();

describe('hunt page test', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntPageModule,
            RouterTestingModule.withRoutes(HUNT_PAGE_ROUTES),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntPageLocalStore, {useFactory: mockHuntPageLocalStore})
        .compileComponents();
  }));

  it('displays hunt information', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageLocalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
    });
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
  });
});
