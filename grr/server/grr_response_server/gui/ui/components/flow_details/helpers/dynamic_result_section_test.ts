import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {Process} from '../../../lib/api/api_interfaces';
import {FlowResult, PaginatedResultView, PreloadedResultView, ResultQuery} from '../../../lib/models/flow';
import {newFlowResult} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {DynamicResultSection} from './dynamic_result_section';
import {HelpersModule} from './module';
import {ResultAccordionHarness} from './testing/result_accordion_harness';


initTestEnvironment();


@Component({template: `<div id="data">{{ data | json }}</div>`})
class TestComponent implements PreloadedResultView<Process> {
  @Input() data!: readonly Process[];
}

const INITIAL_QUERY = {
  count: 10,
  offset: 0
};

@Component({
  template: `
  <div id="totalCount">{{totalCount}}</div>
  <div id="results">{{ results | json }}</div>`
})
class PaginatedTestComponent implements OnInit, PaginatedResultView<Process> {
  @Input() results?: readonly FlowResult[];
  @Input() totalCount!: number;
  @Output() readonly loadResults = new EventEmitter<ResultQuery>();

  ngOnInit() {
    this.loadResults.emit(INITIAL_QUERY);
  }
}

describe('app-dynamic-result-section component', () => {
  let flowResultsLocalStore: FlowResultsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    flowResultsLocalStore = mockFlowResultsLocalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
            RouterTestingModule,
          ],
          declarations: [TestComponent, PaginatedTestComponent],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        // Override ALL providers to mock the GlobalStore that is provided by
        // each component.
        .overrideProvider(
            FlowResultsLocalStore, {useFactory: () => flowResultsLocalStore})
        .compileComponents();
  }));

  it('displays a result accordion that shows the simple result view when toggled',
     async () => {
       const fixture = TestBed.createComponent(DynamicResultSection);
       fixture.componentInstance.section = {
         title: 'Testtitle',
         component: TestComponent,
         query: {type: 'Process'},
         totalResultCount: 1,
         flow: {
           flowId: 'flow123',
           clientId: 'C.123',
         }
       };
       fixture.detectChanges();

       expect(fixture.debugElement.nativeElement.textContent)
           .toContain('Testtitle');

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const resultSection =
           await harnessLoader.getHarness(ResultAccordionHarness);
       await resultSection.toggle();

       flowResultsLocalStore.mockedObservables.results$.next(
           [newFlowResult({payload: {name: 'Testprocess'}})]);
       fixture.detectChanges();

       expect(fixture.debugElement.query(By.css('#data'))
                  .nativeElement.textContent)
           .toContain('Testprocess');
     });

  it('displays a result accordion that shows the paginated result view when toggled',
     async () => {
       const fixture = TestBed.createComponent(DynamicResultSection);
       fixture.componentInstance.section = {
         title: 'Testtitle',
         component: PaginatedTestComponent,
         query: {type: 'Process'},
         totalResultCount: 123,
         flow: {
           flowId: 'flow123',
           clientId: 'C.123',
         }
       };
       fixture.detectChanges();

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const resultSection =
           await harnessLoader.getHarness(ResultAccordionHarness);
       await resultSection.toggle();

       expect(fixture.debugElement.query(By.css('#totalCount'))
                  .nativeElement.textContent)
           .toContain('123');
     });

  it('executes pagination queries and assigns flow results', async () => {
    const fixture = TestBed.createComponent(DynamicResultSection);
    fixture.componentInstance.section = {
      title: 'Testtitle',
      component: PaginatedTestComponent,
      query: {type: 'Process'},
      totalResultCount: 123,
      flow: {
        flowId: 'flow123',
        clientId: 'C.123',
      }
    };
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const resultSection =
        await harnessLoader.getHarness(ResultAccordionHarness);
    await resultSection.toggle();

    expect(flowResultsLocalStore.query).toHaveBeenCalledOnceWith({
      withType: 'Process',
      withTag: undefined,
      flow: {flowId: 'flow123', clientId: 'C.123'},
      count: INITIAL_QUERY.count,
      offset: INITIAL_QUERY.offset
    });

    flowResultsLocalStore.mockedObservables.results$.next(
        [newFlowResult({payload: {name: 'Testprocess'}})]);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('#results'))
               .nativeElement.textContent)
        .toContain('Testprocess');
  });
});
