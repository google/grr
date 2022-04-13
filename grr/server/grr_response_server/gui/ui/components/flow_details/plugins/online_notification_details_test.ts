import {TestBed, waitForAsync} from '@angular/core/testing';

import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {PluginsModule} from './module';
import {OnlineNotificationDetails} from './online_notification_details';


initTestEnvironment();

describe('online-notification-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            PluginsModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('should display the recipient email address', () => {
    const fixture = TestBed.createComponent(OnlineNotificationDetails);
    fixture.componentInstance.flow = newFlow({
      name: 'OnlineNotification',
      clientId: 'C.1234',
      flowId: 'ABCDEF',
      state: FlowState.FINISHED,
      args: {
        email: 'foo@example.com',
      },
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('foo@example.com');
  });
});
