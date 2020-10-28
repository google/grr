import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowChips} from '@app/components/flow_picker/flow_chips';
import {FlowListItem} from '@app/components/flow_picker/flow_list_item';
import {initTestEnvironment} from '@app/testing';
import {FlowPickerModule} from './module';




initTestEnvironment();


describe('FlowChips component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowPickerModule,
          ],

          providers: []
        })
        .compileComponents();
  }));

  const flows: ReadonlyArray<FlowListItem> = [
    {
      name: 'ArtifactCollectorFlow',
      friendlyName: 'Forensic artifacts',
      description: 'Foo'
    },
    {
      name: 'OsqueryFlow',
      friendlyName: 'Osquery',
      description: 'Bar',
    },
  ];

  it('shows nothing by default', () => {
    const fixture = TestBed.createComponent(FlowChips);
    fixture.detectChanges();

    const buttons = fixture.debugElement.queryAll(By.css('button'));
    expect(buttons.length).toBe(0);
  });

  it('shows flows from the provided observable', () => {
    const fixture = TestBed.createComponent(FlowChips);
    fixture.componentInstance.flows = flows;
    fixture.detectChanges();

    const buttons = fixture.debugElement.queryAll(By.css('button'));
    expect(buttons.length).toBe(2);

    expect(buttons[0].nativeElement.innerText).toContain('Forensic artifacts');
    expect(buttons[1].nativeElement.innerText).toContain('Osquery');
  });

  it('emits event when button is clicked', () => {
    const fixture = TestBed.createComponent(FlowChips);
    fixture.componentInstance.flows = flows;
    let selectedFlowListItem: FlowListItem|undefined;
    fixture.componentInstance.flowSelected.subscribe((v: FlowListItem) => {
      selectedFlowListItem = v;
    });
    fixture.detectChanges();

    const buttons = fixture.debugElement.queryAll(By.css('button'));
    buttons[0].nativeElement.click();
    fixture.detectChanges();

    expect(selectedFlowListItem).toBe(flows[0]);
  });
});
