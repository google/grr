import {Component, Input, ViewChild} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowArgsFormModule} from '@app/components/flow_args_form/module';
import {initTestEnvironment} from '@app/testing';

import {ApiBrowserHistoryFlowArgs} from '../../lib/api/api_interfaces';
import {FlowDescriptor} from '../../lib/models/flow';

import {FlowArgsForm} from './flow_args_form';


initTestEnvironment();

const TEST_FLOW_DESCRIPTORS = Object.freeze({
  BrowserHistoryFlow: {
    name: 'BrowserHistoryFlow',
    friendlyName: 'Browser History',
    category: 'Browser',
    defaultArgs: {
      collectChrome: true,
      collectFirefox: true,
      collectInternetExplorer: true,
      collectOpera: true,
      collectSafari: true,
    }
  }
});

@Component({
  template:
      '<flow-args-form [flowDescriptor]="flowDescriptor"></flow-args-form>',
})
class TestHostComponent {
  @Input() flowDescriptor?: FlowDescriptor;
  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;
}

function setUp() {
  return TestBed
      .configureTestingModule({
        imports: [
          NoopAnimationsModule,
          FlowArgsFormModule,
        ],
        declarations: [
          TestHostComponent,
        ],

      })
      .compileComponents();
}

describe('FlowArgsForm Component', () => {
  beforeEach(setUp);

  it('is empty initially', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('renders sub-form correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.BrowserHistoryFlow;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Chrome');
  });

  it('emits form value changes', (done) => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    let counter = 0;

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe((value) => {
      const args = value as ApiBrowserHistoryFlowArgs;
      if (counter === 0) {
        expect(args.collectChrome).toBeTrue();
        counter++;
      } else {
        expect(args.collectChrome).toBeFalse();
        done();
      }
    });

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.BrowserHistoryFlow;
    fixture.detectChanges();

    // This test assumes that the first label in the BrowserHistoryForm is
    // Chrome, which is not ideal, but an effective workaround.
    const label = fixture.debugElement.query(By.css('label')).nativeElement;
    expect(label.innerText).toContain('Chrome');
    label.click();
    fixture.detectChanges();
  });

  it('is empty after flow unselection', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.BrowserHistoryFlow;
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor = undefined;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('shows fallback for non-existent flow form', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.flowDescriptor = {
      name: 'FlowWithoutForm',
      friendlyName: '---',
      category: 'Misc',
      defaultArgs: {},
    };
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText.trim())
        .toContain('Form for selected Flow has not been found');
  });
});


Object.values(TEST_FLOW_DESCRIPTORS).forEach(fd => {
  describe(`FlowArgForm ${fd.name}`, () => {
    beforeEach(setUp);

    it('renders a sub-form', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();

      expect(fixture.nativeElement.innerText.trim()).toBeTruthy();
    });

    it('emits initial form values', (done) => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
          values => {
            expect(values).toBeTruthy();
            done();
          });

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();
    });
  });
});
