import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {newScheduledFlow} from '../../lib/models/model_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {mockScheduledFlowGlobalStore, ScheduledFlowGlobalStoreMock} from '../../store/scheduled_flow_global_store_test_util';
import {UserGlobalStore} from '../../store/user_global_store';
import {mockUserGlobalStore, UserGlobalStoreMock} from '../../store/user_global_store_test_util';

import {ScheduledFlowListModule} from './module';

import {ScheduledFlowList} from './scheduled_flow_list';


initTestEnvironment();



describe('ScheduledFlowList Component', () => {
  let scheduledFlowGlobalStore: ScheduledFlowGlobalStoreMock;
  let userGlobalStore: UserGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    scheduledFlowGlobalStore = mockScheduledFlowGlobalStore();
    userGlobalStore = mockUserGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ScheduledFlowListModule,
          ],

          providers: [
            {
              provide: ScheduledFlowGlobalStore,
              useFactory: () => scheduledFlowGlobalStore,
            },
            {
              provide: ConfigGlobalStore,
              useFactory: mockConfigGlobalStore,
            },
            {
              provide: UserGlobalStore,
              useFactory: () => userGlobalStore,
            },
          ]
        })
        .compileComponents();
  }));

  it('displays scheduled flows', () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    scheduledFlowGlobalStore.scheduledFlowsSubject.next([
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

    userGlobalStore.currentUserSubject.next({name: 'testuser'});

    const scheduledFlow = newScheduledFlow({creator: 'testuser'});
    scheduledFlowGlobalStore.scheduledFlowsSubject.next([scheduledFlow]);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[0].click();

    expect(scheduledFlowGlobalStore.unscheduleFlow)
        .toHaveBeenCalledWith(scheduledFlow.scheduledFlowId);
  });

  it('hides unschedule button when user is not creator', async () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    userGlobalStore.currentUserSubject.next({name: 'testuser'});

    const scheduledFlow = newScheduledFlow({creator: 'differentuser'});
    scheduledFlowGlobalStore.scheduledFlowsSubject.next([scheduledFlow]);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-menu'))).toBeNull();
  });
});
