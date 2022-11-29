import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {HuntState} from '../../../lib/models/hunt';
import {newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
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

  it('displays hunt information', () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);

    expect(huntPageLocalStore.setArgs).toHaveBeenCalled();

    huntPageLocalStore.mockedObservables.results$.next(
        [newHunt({description: 'Collect foobar'})]);
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('Collect foobar');
  });

  it('displays an empty progress for a running hunt without completed clients',
     async () => {
       const fixture = TestBed.createComponent(HuntOverviewPage);
       fixture.detectChanges();

       const huntPageLocalStore =
           injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);
       huntPageLocalStore.mockedObservables.results$.next([newHunt({
         description: 'Collect foobar',
         allClientsCount: BigInt(0),
         completedClientsCount: BigInt(0),
         state: HuntState.STARTED,
       })]);
       fixture.detectChanges();

       // Getting MatProgressBarHarness times out for unknown reasons, so we
       // read the progress bar state from ARIA:
       const progressBar =
           fixture.debugElement.query(By.css('mat-progress-bar'));
       expect(Number(progressBar.attributes['aria-valuenow'])).toEqual(0);
     });

  it('displays a full progress for a completed hunt', async () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();

    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.results$.next([newHunt({
      description: 'Collect foobar',
      allClientsCount: BigInt(10),
      completedClientsCount: BigInt(10),
      state: HuntState.PAUSED,
      safetyLimits: newSafetyLimits({clientLimit: BigInt(99)}),
    })]);
    fixture.detectChanges();

    // Getting MatProgressBarHarness times out for unknown reasons, so we
    // read the progress bar state from ARIA:
    const progressBar = fixture.debugElement.query(By.css('mat-progress-bar'));
    expect(Number(progressBar.attributes['aria-valuenow'])).toEqual(100);
  });

  it('displays a padded progress for running hunts without client limit',
     async () => {
       const fixture = TestBed.createComponent(HuntOverviewPage);
       fixture.detectChanges();

       const huntPageLocalStore =
           injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);
       huntPageLocalStore.mockedObservables.results$.next([newHunt({
         description: 'Collect foobar',
         allClientsCount: BigInt(10),
         completedClientsCount: BigInt(7),
         state: HuntState.STARTED,
         safetyLimits: newSafetyLimits({clientLimit: BigInt(0)}),
       })]);
       fixture.detectChanges();

       const completePercent = 7 / 10 * 100;
       const padding = completePercent * .1;

       // Getting MatProgressBarHarness times out for unknown reasons, so we
       // read the progress bar state from ARIA:
       const progressBar =
           fixture.debugElement.query(By.css('mat-progress-bar'));
       expect(Math.trunc(Number(progressBar.attributes['aria-valuenow'])))
           .toEqual(completePercent - padding);
     });

  it('displays progress as fraction of client limit', async () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();

    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.results$.next([newHunt({
      description: 'Collect foobar',
      allClientsCount: BigInt(10),
      completedClientsCount: BigInt(7),
      state: HuntState.STARTED,
      safetyLimits: newSafetyLimits({clientLimit: BigInt(20)}),
    })]);
    fixture.detectChanges();

    // Getting MatProgressBarHarness times out for unknown reasons, so we
    // read the progress bar state from ARIA:
    const progressBar = fixture.debugElement.query(By.css('mat-progress-bar'));
    expect(Math.trunc(Number(progressBar.attributes['aria-valuenow'])))
        .toEqual(7 / 20 * 100);
  });
});
