import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResultSet} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {ArtifactCollectorFlowDetails} from './artifact_collector_flow_details';
import {PluginsModule} from './module';



initTestEnvironment();

describe('artifact-collector-flow-details component', () => {
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

  it('displays file results', () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        args: {},
      }),
      resultSets: [
        newFlowResultSet({stSize: 123, pathspec: {path: '/foo'}}),
      ],
    };
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo');
    expect(fixture.nativeElement.innerText).toContain('123');
  });
});
