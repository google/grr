import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {HuntState} from '../../../lib/models/hunt';
import {newHunt} from '../../../lib/models/model_test_util';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {mockHuntPageGlobalStore} from '../../../store/hunt_page_global_store_test_util';
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
            HuntPageGlobalStore, {useFactory: mockHuntPageGlobalStore})
        .compileComponents();
  }));

  it('selects huntId based on the route', async () => {
    await TestBed.inject(Router).navigate(['hunts/999']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    fixture.detectChanges();

    expect(huntPageLocalStore.selectHunt).toHaveBeenCalledWith('999');
  });

  it('displays hunt overview information - STARTED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.STARTED,
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection running');
    expect(text).toContain('left');
    // hunt state is STARTED
    expect(text).toContain('Stop collection');
  });

  it('displays hunt overview information - STOPPED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.STOPPED,
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection stopped');
    // hunt state is STOPPED
    expect(text).not.toContain('Stop collection');
  });

  it('Stop button calls stopHunt with correct state', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.STARTED,
    }));
    fixture.detectChanges();

    const stopButton =
        fixture.debugElement.query(By.css('button[name=stop-button]'));
    stopButton.nativeElement.click();
    expect(huntPageLocalStore.stopHunt).toHaveBeenCalledTimes(1);
  });

  it('displays hunt progress information', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      allClientsCount: BigInt(10),
      completedClientsCount: BigInt(3),
      remainingClientsCount: BigInt(7),
      clientsWithResultsCount: BigInt(1),
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('app-hunt-progress'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Total progress');
    expect(text).toContain('~ 10 clients');
    expect(text).toContain('30 %');  // Complete
    expect(text).toContain('70 %');  // In progress
    expect(text).toContain('20 %');  // No results
    expect(text).toContain('10 %');  // With results
  });
});
