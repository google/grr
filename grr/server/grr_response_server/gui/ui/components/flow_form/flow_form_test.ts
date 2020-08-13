import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowFormModule} from '@app/components/flow_form/module';
import {CollectBrowserHistoryArgsBrowser} from '@app/lib/api/api_interfaces';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {ConfigFacade} from '@app/store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '@app/store/config_facade_test_util';
import {initTestEnvironment} from '@app/testing';

import {ClientApproval} from '../../lib/models/client';
import {newClient, newFlowDescriptor} from '../../lib/models/model_test_util';
import {ClientPageFacadeMock, mockClientPageFacade} from '../../store/client_page_facade_test_util';

import {FlowForm} from './flow_form';


initTestEnvironment();

function getSubmit<T>(fixture: ComponentFixture<T>) {
  return fixture.nativeElement.querySelector('button[type=submit]');
}

function validApproval(): ClientApproval {
  return {
    approvalId: '444',
    clientId: 'C.1234',
    requestor: 'testuser',
    reason: 'Approved.',
    status: {type: 'valid'},
    requestedApprovers: ['rick'],
    approvers: ['rick', 'testuser'],
  };
}

describe('FlowForm Component', () => {
  let configFacade: ConfigFacadeMock;
  let clientPageFacade: ClientPageFacadeMock;

  beforeEach(async(() => {
    configFacade = mockConfigFacade();
    clientPageFacade = mockClientPageFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowFormModule,
          ],

          providers: [
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
          ]
        })
        .compileComponents();
  }));

  it('shows no submit button without selected flow', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeNull();

    clientPageFacade.selectedFlowDescriptorSubject.next();
    expect(getSubmit(fixture)).toBeNull();
  });

  it('shows submit button when flow is selected', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageFacade.selectedFlowDescriptorSubject.next(newFlowDescriptor());
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeTruthy();
  });

  it('triggers startFlow on form submit', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(newClient());
    clientPageFacade.selectedFlowDescriptorSubject.next(newFlowDescriptor({
      name: 'CollectBrowserHistory',
      defaultArgs: {
        browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
      }
    }));
    clientPageFacade.latestApprovalSubject.next(validApproval());
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientPageFacade.startFlow).toHaveBeenCalledWith({
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    });
  });

  it('triggers scheduleFlow on form submit without approval', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(newClient());
    clientPageFacade.selectedFlowDescriptorSubject.next(newFlowDescriptor({
      name: 'CollectBrowserHistory',
      defaultArgs: {
        browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
      }
    }));
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientPageFacade.scheduleFlow).toHaveBeenCalledWith({
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    });
  });

  it('shows errors when flow submit fails', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(newClient());
    clientPageFacade.selectedFlowDescriptorSubject.next(newFlowDescriptor());
    clientPageFacade.latestApprovalSubject.next(validApproval());
    fixture.detectChanges();

    clientPageFacade.startFlowStateSubject.next(
        {state: 'error', error: 'foobazzle rapidly disintegrated'});
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('foobazzle rapidly disintegrated');
  });
});
