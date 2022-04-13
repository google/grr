import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowListItem, FlowsByCategory} from '../../components/flow_picker/flow_list_item';
import {FlowsOverview} from '../../components/flow_picker/flows_overview';
import {initTestEnvironment} from '../../testing';

import {FlowPickerModule} from './module';



initTestEnvironment();


describe('FlowsOverview component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowPickerModule,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  const flowsByCategory: FlowsByCategory = new Map([
    [
      'Collectors',
      [
        {
          name: 'ArtifactCollectorFlow',
          friendlyName: 'Forensic artifacts',
          description: 'Foo',
          enabled: true,
        },
        {
          name: 'OsqueryFlow',
          friendlyName: 'Osquery',
          description: 'Bar',
          enabled: true,
        },
      ]
    ],
    [
      'Browser',
      [
        {
          name: 'CollectBrowserHistory',
          friendlyName: 'Collect browser history',
          description: 'Something',
          enabled: true,
        },
      ]
    ],
  ]);

  it('shows each category', () => {
    const fixture = TestBed.createComponent(FlowsOverview);
    fixture.componentInstance.flowsByCategory = flowsByCategory;
    fixture.detectChanges();

    const categories =
        fixture.debugElement.queryAll(By.css('.category .title'));
    expect(categories.length).toBe(2);

    expect(categories[0].nativeElement.innerText).toContain('Browser');
    expect(categories[1].nativeElement.innerText).toContain('Collectors');
  });

  it('shows each flow', () => {
    const fixture = TestBed.createComponent(FlowsOverview);
    fixture.componentInstance.flowsByCategory = flowsByCategory;
    fixture.detectChanges();

    const items = fixture.debugElement.queryAll(By.css('.item'));
    expect(items.length).toBe(3);

    expect(items[0].nativeElement.innerText)
        .toContain('Collect browser history');
    expect(items[1].nativeElement.innerText).toContain('Forensic artifacts');
    expect(items[2].nativeElement.innerText).toContain('Osquery');
  });

  it('emits event when link is clicked', () => {
    const fixture = TestBed.createComponent(FlowsOverview);
    fixture.componentInstance.flowsByCategory = flowsByCategory;
    fixture.detectChanges();

    let selectedFlowListItem: FlowListItem|undefined;
    fixture.componentInstance.flowSelected.subscribe((v: FlowListItem) => {
      selectedFlowListItem = v;
    });
    fixture.detectChanges();

    const links = fixture.debugElement.queryAll(By.css('a'));
    links[0].nativeElement.dispatchEvent(new MouseEvent('click'));
    fixture.detectChanges();

    expect(selectedFlowListItem).toBe(flowsByCategory.get('Browser')![0]);
  });
});
