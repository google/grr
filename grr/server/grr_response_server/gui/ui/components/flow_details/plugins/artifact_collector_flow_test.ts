import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResultSet} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';
import {firstValueFrom} from 'rxjs';

import {ExecuteResponse} from '../../../lib/api/api_interfaces';

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
        newFlowResultSet({stSize: 123, pathspec: {path: '/foo'}}, 'StatEntry'),
      ],
    };
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo');
    expect(fixture.nativeElement.innerText).toContain('123');
  });

  it('displays cmd results', () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    const response: ExecuteResponse = {
      exitStatus: 123,
      request: {
        cmd: '/bin/foo',
        args: ['bar'],
      },
      stderr: btoa('err123'),
      stdout: btoa('out123'),
    };

    fixture.componentInstance.flowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        args: {},
      }),
      resultSets: [
        newFlowResultSet(response, 'ExecuteResponse'),
      ],
    };
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/bin/foo');
    expect(fixture.nativeElement.innerText).toContain('bar');
    expect(fixture.nativeElement.innerText).toContain('err123');
    expect(fixture.nativeElement.innerText).toContain('out123');
  });

  it('loads results on click', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        args: {},
      }),
      resultSets: [],
    };
    fixture.detectChanges();

    const flowResultsQueryPromise =
        firstValueFrom(fixture.componentInstance.flowResultsQuery);

    const button = fixture.debugElement.query(
        By.css('button[aria-label="Load more results"]'));
    expect(button.nativeElement).not.toBeNull();
    button.nativeElement.click();
    fixture.detectChanges();

    const flowResultsQuery = await flowResultsQueryPromise;
    expect(flowResultsQuery.offset).toEqual(0);
    expect(flowResultsQuery.count).toBeGreaterThan(0);
  });

  it('displays fallback link for unknown results', () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);

    fixture.componentInstance.flowListEntry = {
      flow: newFlow({
        state: FlowState.FINISHED,
        args: {},
      }),
      resultSets: [
        newFlowResultSet({}, 'Unknown'),
      ],
    };
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('old UI');
  });
});
