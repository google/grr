import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowFormModule} from '@app/components/flow_form/module';
import {Client} from '@app/lib/models/client';
import {ClientFacade} from '@app/store/client_facade';
import {FlowFacade} from '@app/store/flow_facade';
import {FlowFacadeMock, mockFlowFacade} from '@app/store/flow_facade_test_util';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {FlowForm} from './flow_form';


initTestEnvironment();

function getSubmit<T>(fixture: ComponentFixture<T>) {
  return fixture.nativeElement.querySelector('button[type=submit]');
}

describe('FlowForm Component', () => {
  let selectedClient$: Subject<Client>;
  let flowFacade: FlowFacadeMock;
  let clientFacade: Partial<ClientFacade>;

  beforeEach(async(() => {
    selectedClient$ = new Subject();
    flowFacade = mockFlowFacade();
    clientFacade = {
      selectedClient$,
      startFlow: jasmine.createSpy('startFlow'),
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowFormModule,
          ],

          providers: [
            {provide: FlowFacade, useValue: flowFacade},
            {provide: ClientFacade, useValue: clientFacade},
          ]
        })
        .compileComponents();
  }));

  it('shows no submit button without selected flow', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeNull();

    flowFacade.selectedFlowSubject.next();
    expect(getSubmit(fixture)).toBeNull();
  });

  it('shows submit button when flow is selected', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    flowFacade.selectedFlowSubject.next({
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
    });
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeTruthy();
  });

  it('triggers startFlow on form submit', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    selectedClient$.next({
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {},
      labels: []
    });
    flowFacade.selectedFlowSubject.next({
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
    });
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientFacade.startFlow)
        .toHaveBeenCalledWith('C.1234', 'BrowserHistoryFlow', {
          collectChrome: true,
          collectFirefox: true,
          collectInternetExplorer: true,
          collectOpera: true,
          collectSafari: true,
        });
  });
});
