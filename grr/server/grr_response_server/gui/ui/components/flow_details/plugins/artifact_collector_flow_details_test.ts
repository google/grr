import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {FlowState} from '@app/lib/models/flow';
import {newFlow, newFlowResult} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {ExecuteResponse, PathSpecPathType, RegistryType, StatEntry} from '../../../lib/api/api_interfaces';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {ResultAccordion, Status} from '../helpers/result_accordion';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {ArtifactCollectorFlowDetails} from './artifact_collector_flow_details';
import {PluginsModule} from './module';


initTestEnvironment();


describe('artifact-collector-flow-details component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            PluginsModule,
            RouterTestingModule,
          ],

          providers: []
        })
        // Override ALL providers to mock the GlobalStore that is provided by
        // each component.
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('displays file results ', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });
    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'StatEntry',
      payload: {stSize: '123', pathspec: {path: '/foo'}},
    })]);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.innerText).toContain('/foo');
    expect(fixture.nativeElement.innerText).toContain('123');
  });

  it('displays registry results ', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });

    const statEntry: StatEntry = {
      stSize: '123',
      registryType: RegistryType.REG_BINARY,
      pathspec: {path: 'HKLM\\foo', pathtype: PathSpecPathType.REGISTRY},
    };

    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payloadType: 'StatEntry', payload: statEntry})]);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.innerText).toContain('HKLM\\foo');
    expect(fixture.nativeElement.innerText).toContain('REG_BINARY');
  });

  it('displays cmd results', async () => {
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

    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });
    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payload: response, payloadType: 'ExecuteResponse'})]);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.innerText).toContain('/bin/foo');
    expect(fixture.nativeElement.innerText).toContain('bar');
    expect(fixture.nativeElement.innerText).toContain('err123');
    expect(fixture.nativeElement.innerText).toContain('out123');
  });

  it('loads results on click', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });
    fixture.detectChanges();

    expect(flowResultsLocalStore.queryMore).not.toHaveBeenCalled();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(flowResultsLocalStore.queryMore).toHaveBeenCalled();
  });

  it('displays fallback link for unknown results', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);

    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });
    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payload: {}, payloadType: 'unknown'})]);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.innerText).toContain('old UI');
  });

  it('displays progress result count', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
      progress: {artifacts: [{name: 'foobar', numResults: 3}]},
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    expect(fixture.nativeElement.innerText).toContain('3 results');
  });

  it('displays flow state', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
    });
    fixture.detectChanges();

    const accordion = fixture.debugElement.query(By.directive(ResultAccordion));
    expect(accordion.componentInstance.status).toEqual(Status.SUCCESS);
  });
});
