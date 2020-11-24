import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {DefaultDetails} from '@app/components/flow_details/plugins/default_details';
import {MultiGetFileDetails} from '@app/components/flow_details/plugins/multi_get_file_details';
import {Plugin} from '@app/components/flow_details/plugins/plugin';
import {FlowDescriptor, FlowListEntry, flowListEntryFromFlow} from '@app/lib/models/flow';
import {newFlowListEntry} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {ConfigFacade} from '../../store/config_facade';
import {mockConfigFacade} from '../../store/config_facade_test_util';

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
    [flowListEntry]="flowListEntry"
    [flowDescriptor]="flowDescriptor"

    (flowResultsQuery)="flowResultsQueryTriggered($event)">
</flow-details>`
})
class TestHostComponent {
  flowListEntry: FlowListEntry|undefined;
  flowDescriptor: FlowDescriptor|undefined;

  flowResultsQueryTriggered = jasmine.createSpy('flowResultsQueryTriggered');
}

describe('FlowDetails Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowDetailsModule,
            RouterTestingModule.withRoutes([]),
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: [
            {provide: ConfigFacade, useFactory: mockConfigFacade},
          ]
        })
        .compileComponents();
  }));

  function createComponent(
      flowListEntry: FlowListEntry,
      flowDescriptor?: FlowDescriptor): ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.flowListEntry = flowListEntry;
    fixture.componentInstance.flowDescriptor = flowDescriptor;
    fixture.detectChanges();

    return fixture;
  }

  const SAMPLE_FLOW_LIST_ENTRY = Object.freeze(newFlowListEntry({
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

    fixture.componentInstance.flowListEntry = flowListEntryFromFlow(
        {...SAMPLE_FLOW_LIST_ENTRY.flow, name: 'AnotherFlow'});
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
    FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.flow.name] =
        MultiGetFileDetails;

    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    expect(fixture.debugElement.query(By.directive(DefaultDetails))).toBeNull();
    expect(fixture.debugElement.query(By.directive(MultiGetFileDetails)))
        .not.toBeNull();
  });

  it('propagates flowResultsQuery event from the plugin', () => {
    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);
    const plugin = fixture.debugElement.query(By.directive(DefaultDetails))
                       .componentInstance as Plugin;

    plugin.queryFlowResults({
      offset: 0,
      count: 100,
      withType: 'someType',
      withTag: 'someTag',
    });

    expect(fixture.componentInstance.flowResultsQueryTriggered)
        .toHaveBeenCalledWith({
          flowId: SAMPLE_FLOW_LIST_ENTRY.flow.flowId,
          withType: 'someType',
          withTag: 'someTag',
          offset: 0,
          count: 100,
        });
  });

  afterEach(() => {
    delete FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.flow.name];
  });
});
