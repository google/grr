import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {newScheduledFlow} from '../../lib/models/model_test_util';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ClientPageFacadeMock, mockClientPageFacade} from '../../store/client_page_facade_test_util';

import {ScheduledFlowListModule} from './module';

import {ScheduledFlowList} from './scheduled_flow_list';

initTestEnvironment();

describe('ScheduledFlowList Component', () => {
  let clientPageFacade: ClientPageFacadeMock;

  // TODO(user): Change to waitForAsync once we run on Angular 10, which
  //  in turn requires TypeScript 3.9.
  // tslint:disable-next-line:deprecation
  beforeEach(async(() => {
    clientPageFacade = mockClientPageFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ScheduledFlowListModule,
          ],

          providers: [
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
          ]
        })
        .compileComponents();
  }));

  it('displays scheduled flows', () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    clientPageFacade.scheduledFlowsSubject.next([
      newScheduledFlow({flowName: 'CollectSingleFile'}),
      newScheduledFlow({flowName: 'CollectBrowserHistory'}),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('CollectSingleFile');
    expect(text).toContain('CollectBrowserHistory');
  });

  it('unschedules when the button is clicked', () => {
    const fixture = TestBed.createComponent(ScheduledFlowList);
    fixture.detectChanges();

    const scheduledFlow = newScheduledFlow();
    clientPageFacade.scheduledFlowsSubject.next([scheduledFlow]);
    fixture.detectChanges();

    const button =
        fixture.debugElement.query(By.css('button[aria-label="Unschedule"]'));
    button.triggerEventHandler('click', null);

    expect(clientPageFacade.unscheduleFlow)
        .toHaveBeenCalledWith(scheduledFlow.scheduledFlowId);
  });
});
