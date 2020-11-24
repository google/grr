import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowDescriptor} from '@app/lib/models/flow';
import {newFlowDescriptorMap} from '@app/lib/models/model_test_util';
import {ClientPageFacadeMock, mockClientPageFacade} from '@app/store/client_page_facade_test_util';
import {ConfigFacade} from '@app/store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '@app/store/config_facade_test_util';
import {initTestEnvironment} from '@app/testing';

import {ClientPageFacade} from '../../store/client_page_facade';

import {FlowPicker} from './flow_picker';
import {FlowPickerModule} from './module';


initTestEnvironment();

function highlighted(): jasmine.AsymmetricMatcher<HTMLElement> {
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
        name: 'CollectSingleFile',
        friendlyName: 'Collect Single File',
        category: 'Filesystem',
      },
      {
        name: 'CollectBrowserHistory',
        friendlyName: 'Collect Browser History',
        category: 'Browser',
      });
}

describe('FlowPicker Component', () => {
  let configFacade: ConfigFacadeMock;
  let clientPageFacade: ClientPageFacadeMock;

  beforeEach(async(() => {
    configFacade = mockConfigFacade();
    clientPageFacade = mockClientPageFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowPickerModule,
          ],

          providers: [
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: ClientPageFacade, useFactory: () => clientPageFacade}
          ]
        })
        .compileComponents();
  }));

  it('loads and displays FlowDescriptors', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    configFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collect Single File');
    expect(text).toContain('Collect Browser History');
    expect(text).toContain('Filesystem');
    expect(text).toContain('Browser');
  });

  it('highlights all FlowDescriptors with no text input', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    configFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
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


    configFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    fixture.componentInstance.textInput.setValue('file');
    fixture.detectChanges();

    const btns: HTMLButtonElement[] =
        Array.from(fixture.nativeElement.querySelectorAll('button'));
    expect(btns.find(withText('Collect Single File'))).toEqual(highlighted());
    expect(btns.find(withText('Collect Browser History')))
        .not.toEqual(highlighted());
  });

  it('selects a Flow on click', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    configFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();
    const btns: HTMLButtonElement[] =
        Array.from(fixture.nativeElement.querySelectorAll('button'));
    btns.find(withText('Collect Single File'))!.click();
    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('CollectSingleFile');
  });

  it('selects a Flow on enter press', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    configFacade.flowDescriptorsSubject.next(makeFlowDescriptors());
    fixture.detectChanges();

    fixture.componentInstance.textInput.setValue('browser');
    fixture.detectChanges();

    // Calling submit() unexpectedly reloads the page, which causes tests to
    // fail. Dispatching the submit event manually works, so does production.
    fixture.componentInstance.form.nativeElement.dispatchEvent(
        new Event('submit'));
    expect(clientPageFacade.startFlowConfiguration)
        .toHaveBeenCalledWith('CollectBrowserHistory');
  });

  it('can unselect flows', () => {
    const fixture = TestBed.createComponent(FlowPicker);
    fixture.detectChanges();

    const fds = makeFlowDescriptors();
    configFacade.flowDescriptorsSubject.next(fds);
    clientPageFacade.selectedFlowDescriptorSubject.next(
        fds.get('CollectBrowserHistory'));
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Collect Browser History');

    // TODO(user): Preferrably, we would test the actual UI and not only the
    //  underlying controller method. Removing of MatChip is hard to trigger,
    //  somehow manual KeyboardEvents are not processed in order.
    fixture.componentInstance.unselectFlow();
    expect(clientPageFacade.stopFlowConfiguration).toHaveBeenCalled();
  });
});
