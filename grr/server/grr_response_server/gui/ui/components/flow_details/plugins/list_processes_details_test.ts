import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResultSet} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {ListProcessesDetails} from './list_processes_details';
import {PluginsModule} from './module';



initTestEnvironment();

describe('ListProcessesDetails component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
          ],

          providers: []
        })
        .compileComponents();
  }));

  it('displays process results', () => {
    const fixture = TestBed.createComponent(ListProcessesDetails);
    fixture.componentInstance.flowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        args: {},
      }),
      resultSets: [
        newFlowResultSet({pid: 0, cmdline: ['/foo', 'bar']}),
      ],
    };
    fixture.detectChanges();

    fixture.debugElement.query(By.css('button'))
        .triggerEventHandler('click', undefined);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo');
  });
});
