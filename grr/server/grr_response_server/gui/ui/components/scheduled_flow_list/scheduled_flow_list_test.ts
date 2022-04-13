import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newScheduledFlow} from '../../lib/models/model_test_util';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {UserGlobalStore} from '../../store/user_global_store';
import {initTestEnvironment} from '../../testing';

import {ScheduledFlowListModule} from './module';
import {ScheduledFlowList} from './scheduled_flow_list';


initTestEnvironment();


describe('ScheduledFlowList Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ScheduledFlowListModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays scheduled flows', () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    injectMockStore(ScheduledFlowGlobalStore)
        .mockedObservables.scheduledFlows$.next([
          newScheduledFlow({flowName: 'CollectSingleFile'}),
          newScheduledFlow({flowName: 'CollectBrowserHistory'}),
        ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('CollectSingleFile');
    expect(text).toContain('CollectBrowserHistory');
  });

  it('unschedules when the button is clicked', async () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'testuser',
      canaryMode: false,
      huntApprovalRequired: false,
    });

    const scheduledFlow = newScheduledFlow({creator: 'testuser'});
    injectMockStore(ScheduledFlowGlobalStore)
        .mockedObservables.scheduledFlows$.next([scheduledFlow]);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[0].click();

    expect(injectMockStore(ScheduledFlowGlobalStore).unscheduleFlow)
        .toHaveBeenCalledWith(scheduledFlow.scheduledFlowId);
  });

  it('hides unschedule button when user is not creator', async () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'testuser',
      canaryMode: false,
      huntApprovalRequired: false,
    });

    const scheduledFlow = newScheduledFlow({creator: 'differentuser'});
    injectMockStore(ScheduledFlowGlobalStore)
        .mockedObservables.scheduledFlows$.next([scheduledFlow]);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-menu'))).toBeNull();
  });
});
