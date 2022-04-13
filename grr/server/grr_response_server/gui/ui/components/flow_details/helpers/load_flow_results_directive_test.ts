import {Component, Input} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowResult} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {LoadFlowResultsDirective} from './load_flow_results_directive';
import {HelpersModule} from './module';

@Component({selector: 'test-inner', template: ''})
class InnerComponent {
  @Input() results!: ReadonlyArray<FlowResult>;
  @Input() queryMore!: (c: number) => void;
}

@Component({
  template:
      `<test-inner *loadFlowResults="query; let results=results; let queryMore=queryMore;" [results]="results" [queryMore]="queryMore"></test-inner>`
})
class TestHostComponent<R> {
  @Input() query!: LoadFlowResultsDirective<R>['loadFlowResults'];
}

initTestEnvironment();

describe('LoadFlowResultsDirective', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          declarations: [
            InnerComponent,
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('queries FlowResultsLocalStore', () => {
    const q = Object.freeze({
      flow: {flowId: '12', clientId: 'C.1'},
      withTag: 'a',
      WithType: 'b',
      offset: 12,
      count: 34,
    });

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.query = q;
    fixture.detectChanges();

    expect(flowResultsLocalStore.query).toHaveBeenCalledWith(q);
  });

  it('makes results available', () => {
    const q = Object.freeze({
      flow: {flowId: '12', clientId: 'C.1'},
      withTag: 'a',
      WithType: 'b',
      offset: 12,
      count: 34,
    });

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.query = q;
    fixture.detectChanges();

    const inner = fixture.debugElement.query(By.directive(InnerComponent))
                      .componentInstance as InnerComponent;


    flowResultsLocalStore.mockedObservables.results$.next([
      newFlowResult({payload: {foo: 42}}),
    ]);
    fixture.detectChanges();


    expect(inner.results).toEqual([jasmine.objectContaining(
        {payload: {foo: 42}})]);
  });

  it('passes through queryMore', () => {
    const q = Object.freeze({
      flow: {flowId: '12', clientId: 'C.1'},
      withTag: 'a',
      WithType: 'b',
      offset: 12,
      count: 34,
    });

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.query = q;
    fixture.detectChanges();

    const inner = fixture.debugElement.query(By.directive(InnerComponent))
                      .componentInstance as InnerComponent;

    expect(flowResultsLocalStore.queryMore).not.toHaveBeenCalled();
    inner.queryMore(5);

    expect(flowResultsLocalStore.queryMore).toHaveBeenCalledWith(5);
  });
});
