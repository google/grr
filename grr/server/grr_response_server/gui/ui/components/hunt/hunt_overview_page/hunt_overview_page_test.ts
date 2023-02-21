import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiListHuntsArgsRobotFilter} from '../../../lib/api/api_interfaces';
import {HuntState} from '../../../lib/models/hunt';
import {newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {injectMockStore, mockHuntOverviewPageLocalStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {HuntFilter, HuntOverviewPage} from './hunt_overview_page';
import {HuntOverviewPageModule} from './module';

initTestEnvironment();

describe('app-hunt-overview-page', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RouterTestingModule,
            HuntOverviewPageModule,
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

  it('displays human hunts by default', () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);

    expect(huntPageLocalStore.setArgs).toHaveBeenCalledWith({
      robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS
    });

    huntPageLocalStore.mockedObservables.results$.next([
      newHunt({creator: 'human', isRobot: false}),
    ]);
    fixture.detectChanges();

    const title = fixture.debugElement.query(By.css('h2'));
    expect(title.nativeElement.textContent).toContain('human');

    const cards = fixture.debugElement.queryAll(By.css('.split-card'));
    expect(cards.length).toEqual(1);
    expect(cards[0].nativeElement.textContent).toContain('human');
  });

  it('filter updates list', async () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const huntFilterHarness = await loader.getHarness(
        MatSelectHarness.with({selector: '[name="hunt-filter"]'}));
    await huntFilterHarness.clickOptions({text: HuntFilter.ALL_HUNTS});
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);

    expect(huntPageLocalStore.setArgs).toHaveBeenCalledWith({
      robotFilter: ApiListHuntsArgsRobotFilter.UNKNOWN
    });

    huntPageLocalStore.mockedObservables.results$.next([
      newHunt({creator: 'human', isRobot: false}),
      newHunt({creator: 'robot', isRobot: true})
    ]);
    fixture.detectChanges();

    const title = fixture.debugElement.query(By.css('h2'));
    expect(title.nativeElement.textContent).toContain('All');

    const cards = fixture.debugElement.queryAll(By.css('.split-card'));
    expect(cards.length).toEqual(2);
    expect(cards[0].nativeElement.textContent).toContain('human');
    expect(cards[1].nativeElement.textContent).toContain('robot');
  });

  it('displays hunt information', () => {
    const fixture = TestBed.createComponent(HuntOverviewPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntOverviewPageLocalStore, fixture.debugElement);

    expect(huntPageLocalStore.setArgs).toHaveBeenCalled();

    huntPageLocalStore.mockedObservables.results$.next([newHunt({
      description: 'Collect foobar',
      creator: 'baz',
      created: new Date('1/1/1900'),
      flowName: 'SomeFlow',
      safetyLimits: newSafetyLimits({clientLimit: BigInt(1000)}),
    })]);
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('Collect foobar');
    expect(fixture.debugElement.nativeElement.textContent).toContain('baz');
    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('1900-01-01');

    const argsAccordion =
        fixture.debugElement.query(By.css('result-accordion'));
    expect(argsAccordion).toBeTruthy();
    expect(argsAccordion.nativeElement.textContent).toContain('arguments');


    argsAccordion.query(By.css('.expansion-indicator')).nativeElement.click();
    fixture.detectChanges();

    expect(argsAccordion.nativeElement.textContent).toContain('SomeFlow');
    expect(argsAccordion.nativeElement.textContent).toContain('1000 clients');
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
         state: HuntState.RUNNING,
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
         state: HuntState.RUNNING,
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
      state: HuntState.RUNNING,
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
