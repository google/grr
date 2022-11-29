import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {FlowState} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {InterrogateDetails} from './interrogate_details';
import {PluginsModule} from './module';



initTestEnvironment();

describe('app-interrogate-details component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
            RouterTestingModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('does not show link when flow is in progress', () => {
    const fixture = TestBed.createComponent(InterrogateDetails);
    fixture.componentInstance.flow = newFlow({
      flowId: '1234',
      name: 'Interrogate',
      state: FlowState.RUNNING,
    });
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('a.header'));
    expect(link).toBeNull();
  });

  it('links to client metadata drawer with sourceFlowId', () => {
    const fixture = TestBed.createComponent(InterrogateDetails);
    fixture.componentInstance.flow = newFlow({
      clientId: 'C.1111',
      flowId: '1234',
      name: 'Interrogate',
      state: FlowState.FINISHED,
    });
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('a.header'));
    expect(link.attributes['href']).toContain('C.1111');
    expect(link.attributes['href']).toContain('1234');
  });
});
