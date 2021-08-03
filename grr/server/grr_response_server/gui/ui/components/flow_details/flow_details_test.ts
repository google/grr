import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {DefaultDetails} from '@app/components/flow_details/plugins/default_details';
import {MultiGetFileDetails} from '@app/components/flow_details/plugins/multi_get_file_details';
import {Flow, FlowDescriptor} from '@app/lib/models/flow';
import {newFlow} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {STORE_PROVIDERS} from '../../store/store_test_providers';

import {FlowDetailsModule} from './module';

import {FLOW_DETAILS_PLUGIN_REGISTRY} from './plugin_registry';



initTestEnvironment();

// TestHostComponent is needed in order to trigger change detection in the
// underlying flow-details directive. Creating a standalone flow-details
// instance with createComponent doesn't trigger the ngOnChanges lifecycle
// hook:
// https://stackoverflow.com/questions/37408801/testing-ngonchanges-lifecycle-hook-in-angular-2
@Component({
  template: `
<flow-details
    [flow]="flow"
    [flowDescriptor]="flowDescriptor">
</flow-details>`
})
class TestHostComponent {
  flow: Flow|undefined;
  flowDescriptor: FlowDescriptor|undefined;
}

describe('FlowDetails Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowDetailsModule,
            RouterTestingModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: [
            ...STORE_PROVIDERS,
          ]
        })
        .compileComponents();
  }));

  function createComponent(flow: Flow, flowDescriptor?: FlowDescriptor):
      ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.flow = flow;
    fixture.componentInstance.flowDescriptor = flowDescriptor;
    fixture.detectChanges();

    return fixture;
  }

  const SAMPLE_FLOW_LIST_ENTRY = Object.freeze(newFlow({
    flowId: '42',
    lastActiveAt: new Date('2019-09-23T12:00:00+0000'),
    startedAt: new Date('2019-08-23T12:00:00+0000'),
    name: 'SampleFlow',
    creator: 'testuser',
  }));

  const SAMPLE_FLOW_DESCRIPTOR = Object.freeze({
    name: 'SampleFlow',
    friendlyName: 'Sample Flow',
    category: 'Some category',
    defaultArgs: {},
  });

  it('displays flow name when flow descriptor is not set', () => {
    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('SampleFlow');
    expect(text).toContain('Aug 23, 2019');
    expect(text).toContain('testuser');
  });

  it('displays flow friendly name if flow descriptor is set', () => {
    const fixture =
        createComponent(SAMPLE_FLOW_LIST_ENTRY, SAMPLE_FLOW_DESCRIPTOR);

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('SampleFlow');
    expect(text).toContain('Sample Flow');
  });

  it('displays new flow on "flow" binding update', () => {
    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    fixture.componentInstance.flow =
        newFlow({...SAMPLE_FLOW_LIST_ENTRY, name: 'AnotherFlow'});
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('SampleFlow');
    expect(text).toContain('AnotherFlow');
  });

  it('uses the default plugin if no dedicated plugins is found', () => {
    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    expect(fixture.debugElement.query(By.directive(DefaultDetails)))
        .not.toBeNull();
  });

  it('uses dedicated plugin if available', () => {
    FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.name] =
        MultiGetFileDetails;

    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    expect(fixture.debugElement.query(By.directive(DefaultDetails))).toBeNull();
    expect(fixture.debugElement.query(By.directive(MultiGetFileDetails)))
        .not.toBeNull();
  });

  afterEach(() => {
    delete FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.name];
  });
});
