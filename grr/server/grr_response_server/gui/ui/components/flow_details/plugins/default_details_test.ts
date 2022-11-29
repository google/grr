import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {newFlow} from '../../../lib/models/model_test_util';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {FlowResultsLocalStoreMock, mockFlowResultsLocalStore} from '../../../store/flow_results_local_store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ProcessView} from '../../data_renderers/process/process_view';
import {DynamicResultSection} from '../helpers/dynamic_result_section';

import {DefaultDetails} from './default_details';
import {PluginsModule} from './module';


initTestEnvironment();


describe('app-default-details component', () => {
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

  it('displays a dynamic-result-section for the flow result view section',
     async () => {
       const fixture = TestBed.createComponent(DefaultDetails);
       fixture.componentInstance.flow = newFlow({
         flowId: 'flow123',
         clientId: 'C.123',
         name: 'ListProcesses',
         args: {},
         resultCounts: [{count: 5, type: 'Process'}],
       });
       fixture.detectChanges();

       expect(
           fixture.debugElement.queryAll(By.css('app-dynamic-result-section'))
               .length)
           .toEqual(1);

       const section =
           fixture.debugElement.query(By.directive(DynamicResultSection));
       expect(section.componentInstance.section)
           .toEqual(jasmine.objectContaining({
             component: ProcessView,
             query: {
               type: 'Process',
             },
             totalResultCount: 5,
             flow: jasmine.objectContaining({
               flowId: 'flow123',
               clientId: 'C.123',
             })
           }));
     });
});
