import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ExecuteResponse, PathSpecPathType, StatEntry, StatEntryRegistryType} from '../../../lib/api/api_interfaces';
import {FlowState} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ResultAccordionHarness} from '../helpers/testing/result_accordion_harness';

import {ArtifactCollectorFlowDetails} from './artifact_collector_flow_details';
import {PluginsModule} from './module';

initTestEnvironment();


describe('app-artifact-collector-flow-details component', () => {
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
          providers: [],
          teardown: {destroyAfterEach: false}
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
      progress: {artifacts: [{name: 'foobar', numResults: 1}]},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult({
      payloadType: 'StatEntry',
      payload: {
        stSize: '123',
        pathspec: {path: '/foo', pathtype: PathSpecPathType.OS},
      },
    })]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/foo');
    expect(fixture.nativeElement.innerText).toContain('123');
  });

  it('displays registry results ', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
      progress: {artifacts: [{name: 'foobar', numResults: 1}]},
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    const statEntry: StatEntry = {
      stSize: '123',
      registryType: StatEntryRegistryType.REG_BINARY,
      pathspec: {path: 'HKLM\\foo', pathtype: PathSpecPathType.REGISTRY},
    };

    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payloadType: 'StatEntry', payload: statEntry})]);
    fixture.detectChanges();

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
      progress: {artifacts: [{name: 'foobar', numResults: 1}]},
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payload: response, payloadType: 'ExecuteResponse'})]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('/bin/foo');
    expect(fixture.nativeElement.innerText).toContain('bar');
    expect(fixture.nativeElement.innerText).toContain('err123');
    expect(fixture.nativeElement.innerText).toContain('out123');
  });

  it('displays multiple artifacts', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);

    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foo', 'bar', 'baz']},
      progress: {
        artifacts: [
          {name: 'foo', numResults: 1},
          {name: 'bar', numResults: 2},
          {name: 'baz', numResults: 0},
        ]
      },
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordions =
        await harnessLoader.getAllHarnesses(ResultAccordionHarness);

    expect(resultAccordions.length).toEqual(3);
    expect(fixture.nativeElement.innerText).toMatch(/foo\s*1 result/g);
    expect(fixture.nativeElement.innerText).toMatch(/bar\s*2 results/g);
    expect(fixture.nativeElement.innerText).toMatch(/baz\s*0 results/g);
  });

  it('loads results on click', async () => {
    const fixture = TestBed.createComponent(ArtifactCollectorFlowDetails);
    fixture.componentInstance.flow = newFlow({
      state: FlowState.FINISHED,
      args: {artifactList: ['foobar']},
      progress: {artifacts: [{name: 'foobar', numResults: 1}]},
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
      progress: {artifacts: [{name: 'foobar', numResults: 1}]},
    });
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultAccordionHarness =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultAccordionHarness.toggle();

    flowResultsLocalStore.mockedObservables.results$.next([newFlowResult(
        {payload: {}, payloadType: 'unknown', tag: 'artifact:foobar'})]);
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('old UI');
  });
});
