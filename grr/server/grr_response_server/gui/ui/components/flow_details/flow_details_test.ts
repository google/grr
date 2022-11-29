import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {DefaultDetails} from '../../components/flow_details/plugins/default_details';
import {MultiGetFileDetails} from '../../components/flow_details/plugins/multi_get_file_details';
import {getExportedResultsCsvUrl} from '../../lib/api/http_api_service';
import {Flow, FlowDescriptor, FlowState} from '../../lib/models/flow';
import {newFlow} from '../../lib/models/model_test_util';
import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER, initTestEnvironment} from '../../testing';

import {FlowDetails} from './flow_details';
import {FlowDetailsModule} from './module';
import {FLOW_DETAILS_PLUGIN_REGISTRY} from './plugin_registry';
import {Plugin} from './plugins/plugin';

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
    [flowDescriptor]="flowDescriptor"
    [showContextMenu]="showContextMenu">
</flow-details>`
})
class TestHostComponent {
  flow: Flow|undefined;
  flowDescriptor: FlowDescriptor|undefined;
  showContextMenu: boolean|undefined;
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
            DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function createComponent(
      flow: Flow, flowDescriptor?: FlowDescriptor,
      showContextMenu?: boolean): ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.flow = flow;
    fixture.componentInstance.flowDescriptor = flowDescriptor;
    fixture.componentInstance.showContextMenu = showContextMenu;
    fixture.detectChanges();

    return fixture;
  }

  const SAMPLE_FLOW_LIST_ENTRY = Object.freeze(newFlow({
    flowId: '42',
    lastActiveAt: new Date('2019-09-23T12:00:00+0000'),
    startedAt: new Date('2019-08-23T12:00:00+0000'),
    name: 'SampleFlow',
    creator: 'testuser',
    resultCounts: [],
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
    expect(text).toContain('2019');
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

  it('falls back to default view if result metadata is not present', () => {
    FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.name] =
        MultiGetFileDetails;

    const entry = {
      ...SAMPLE_FLOW_LIST_ENTRY,
      resultCounts: undefined,
    };
    const fixture = createComponent(entry);

    expect(fixture.debugElement.query(By.directive(DefaultDetails)))
        .not.toBeNull();
  });

  it('does NOT display flow arguments if flow descriptor is not set', () => {
    const fixture = createComponent(SAMPLE_FLOW_LIST_ENTRY);

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).not.toContain('Flow arguments');
  });

  it('displays flow arguments if flow descriptor is set', () => {
    const fixture =
        createComponent(SAMPLE_FLOW_LIST_ENTRY, SAMPLE_FLOW_DESCRIPTOR);

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Flow arguments');
  });

  it('does NOT display download button when flow is NOT finished', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      state: FlowState.RUNNING,
    });

    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Download');
  });

  it('does NOT display download button when flow is has no results', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      state: FlowState.FINISHED,
      resultCounts: [],
    });

    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('Download');
  });

  it('displays download button when flow has results', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      flowId: '456',
      clientId: 'C.123',
      state: FlowState.FINISHED,
      resultCounts: [{type: 'Foo', count: 1}],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Download');
    expect(fixture.debugElement.query(By.css('.export-button'))
               .nativeElement.attributes.href?.value)
        .toEqual(getExportedResultsCsvUrl('C.123', '456'));
  });

  it('displays download options in menu when flow has results', async () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      flowId: '456',
      clientId: 'C.123',
      state: FlowState.FINISHED,
      resultCounts: [{type: 'Foo', count: 1}],
    });
    fixture.detectChanges();

    const detailsComponent: Plugin =
        fixture.debugElement.query(By.directive(FlowDetails))
            .componentInstance.detailsComponent.instance;
    const declaredMenuItems =
        detailsComponent.getExportMenuItems(detailsComponent.flow);

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const renderedMenuItems = await menu.getItems();

    // SAMPLE_FLOW_LIST_ENTRY renders DefaultDetails as fallback, which contains
    // the default download options from Plugin.
    expect(renderedMenuItems.length).toEqual(declaredMenuItems.length - 1);
    for (let i = 0; i < renderedMenuItems.length; i++) {
      expect(await renderedMenuItems[i].getText())
          .toEqual(declaredMenuItems[i + 1].title);
    }
  });

  it('displays "0 results" if flow has no results', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      flowId: '456',
      clientId: 'C.123',
      state: FlowState.FINISHED,
      resultCounts: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('0 results');
  });

  it('hides "0 results" if flow is still running', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      flowId: '456',
      clientId: 'C.123',
      state: FlowState.RUNNING,
      resultCounts: [],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).not.toContain('0 results');
  });


  it('displays total result count', () => {
    const fixture = createComponent({
      ...SAMPLE_FLOW_LIST_ENTRY,
      flowId: '456',
      clientId: 'C.123',
      state: FlowState.FINISHED,
      resultCounts: [{type: 'Foo', count: 1}, {type: 'Bar', count: 3}],
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('4 results');
  });

  afterEach(() => {
    delete FLOW_DETAILS_PLUGIN_REGISTRY[SAMPLE_FLOW_LIST_ENTRY.name];
  });

  it('displays flow context menu button', () => {
    const fixture =
        createComponent(SAMPLE_FLOW_LIST_ENTRY, SAMPLE_FLOW_DESCRIPTOR, true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.menu-button'))).toBeTruthy();
  });

  it('hides flow context menu button', () => {
    const fixture =
        createComponent(SAMPLE_FLOW_LIST_ENTRY, SAMPLE_FLOW_DESCRIPTOR, false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.menu-button'))).toBeFalsy();
  });
});
