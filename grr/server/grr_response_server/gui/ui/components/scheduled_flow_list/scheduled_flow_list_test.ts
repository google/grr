import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {newScheduledFlow} from '../../lib/models/model_test_util';
import {ConfigFacade} from '../../store/config_facade';
import {mockConfigFacade} from '../../store/config_facade_test_util';
import {ScheduledFlowFacade} from '../../store/scheduled_flow_facade';
import {mockScheduledFlowFacade, ScheduledFlowFacadeMock} from '../../store/scheduled_flow_facade_test_util';
import {UserFacade} from '../../store/user_facade';
import {mockUserFacade, UserFacadeMock} from '../../store/user_facade_test_util';

import {ScheduledFlowListModule} from './module';

import {ScheduledFlowList} from './scheduled_flow_list';


initTestEnvironment();



describe('ScheduledFlowList Component', () => {
  let scheduledFlowFacade: ScheduledFlowFacadeMock;
  let userFacade: UserFacadeMock;

  beforeEach(waitForAsync(() => {
    scheduledFlowFacade = mockScheduledFlowFacade();
    userFacade = mockUserFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ScheduledFlowListModule,
          ],

          providers: [
            {
              provide: ScheduledFlowFacade,
              useFactory: () => scheduledFlowFacade,
            },
            {
              provide: ConfigFacade,
              useFactory: mockConfigFacade,
            },
            {
              provide: UserFacade,
              useFactory: () => userFacade,
            },
          ]
        })
        .compileComponents();
  }));

  it('displays scheduled flows', () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    scheduledFlowFacade.scheduledFlowsSubject.next([
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

    userFacade.currentUserSubject.next({name: 'testuser'});

    const scheduledFlow = newScheduledFlow({creator: 'testuser'});
    scheduledFlowFacade.scheduledFlowsSubject.next([scheduledFlow]);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[0].click();

    expect(scheduledFlowFacade.unscheduleFlow)
        .toHaveBeenCalledWith(scheduledFlow.scheduledFlowId);
  });

  it('hides unschedule button when user is not creator', async () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    userFacade.currentUserSubject.next({name: 'testuser'});

    const scheduledFlow = newScheduledFlow({creator: 'differentuser'});
    scheduledFlowFacade.scheduledFlowsSubject.next([scheduledFlow]);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-menu'))).toBeNull();
  });
});
