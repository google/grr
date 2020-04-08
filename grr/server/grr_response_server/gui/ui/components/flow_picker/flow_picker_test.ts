import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowDescriptor} from '@app/lib/models/flow';
import {newFlowDescriptorMap} from '@app/lib/models/model_test_util';
import {FlowFacade} from '@app/store/flow_facade';
import {FlowFacadeMock, mockFlowFacade} from '@app/store/flow_facade_test_util';
import {initTestEnvironment} from '@app/testing';

import {FlowPicker} from './flow_picker';


initTestEnvironment();

function highlighted(): jasmine.AsymmetricMatcher<unknown> {
  return {
    asymmetricMatch: (el: HTMLElement) => !el.classList.contains('faded'),
    jasmineToString: () => 'highlighted',
  };
}

function withText(text: string) {
  return (el: HTMLElement) => el.textContent!.includes(text);
}

function makeFlowDescriptors(): ReadonlyMap<string, FlowDescriptor> {
  return newFlowDescriptorMap(
      {
        name: 'ClientSideFileFinder',
        friendlyName: 'Get File',
        category: 'Filesystem',
      },
      {
        name: 'ListProcesses',
        friendlyName: 'Get Processes',
        category: 'OS',
      });
}

describe('FlowPicker Component', () => {
  let flowFacade: FlowFacadeMock;

  beforeEach(async(() => {
    flowFacade = mockFlowFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
          ],

          providers: [{provide: FlowFacade, useValue: flowFacade}]
        })
        .compileComponents();
  }));

  it('loads and displays FlowDescriptors', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    expect(flowFacade.listFlowDescriptors).toHaveBeenCalled();
    flowFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Get File');
    expect(text).toContain('Get Processes');
    expect(text).toContain('Filesystem');
    expect(text).toContain('OS');
  });

  it('highlights all FlowDescriptors with no text input', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    expect(flowFacade.listFlowDescriptors).toHaveBeenCalled();
    flowFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    const btns: NodeListOf<HTMLButtonElement> =
        fixture.nativeElement.querySelectorAll('button');
    expect(btns.length).toEqual(2);
    expect(btns.item(0)).toEqual(highlighted());
    expect(btns.item(1)).toEqual(highlighted());
  });

  it('highlights FlowDescriptors that match text input', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    expect(flowFacade.listFlowDescriptors).toHaveBeenCalled();

    flowFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    fixture.componentInstance.textInput.setValue('file');
    fixture.detectChanges();

    const btns: HTMLButtonElement[] =
        Array.from(fixture.nativeElement.querySelectorAll('button'));
    expect(btns.find(withText('Get File'))).toEqual(highlighted());
    expect(btns.find(withText('Get Processes'))).not.toEqual(highlighted());
  });

  it('selects a Flow on click', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    expect(flowFacade.listFlowDescriptors).toHaveBeenCalled();
    flowFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();
    const btns: HTMLButtonElement[] =
        Array.from(fixture.nativeElement.querySelectorAll('button'));
    btns.find(withText('Get File'))!.click();
    expect(flowFacade.selectFlow).toHaveBeenCalledWith('ClientSideFileFinder');
  });

  it('selects a Flow on enter press', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    expect(flowFacade.listFlowDescriptors).toHaveBeenCalled();
    flowFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    fixture.componentInstance.textInput.setValue('process');
    fixture.detectChanges();

    // Calling submit() unexpectedly reloads the page, which causes tests to
    // fail. Dispatching the submit event manually works, so does production.
    fixture.componentInstance.form.nativeElement.dispatchEvent(
        new Event('submit'));
    expect(flowFacade.selectFlow).toHaveBeenCalledWith('ListProcesses');
  });

  it('can unselect flows', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const fds = makeFlowDescriptors();
    flowFacade.flowDescriptorsSubject.next(fds);
    flowFacade.selectedFlowSubject.next(fds.get('ListProcesses'));
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Get Processes');

    // TODO(user): Preferrably, we would test the actual UI and not only the
    //  underlying controller method. Removing of MatChip is hard to trigger,
    //  somehow manual KeyboardEvents are not processed in order.
    fixture.componentInstance.unselectFlow();
    expect(flowFacade.unselectFlow).toHaveBeenCalled();
  });
});
