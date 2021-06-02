import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowFormModule} from '@app/components/flow_form/module';
import {CollectBrowserHistoryArgsBrowser} from '@app/lib/api/api_interfaces';
import {ClientPageGlobalStore} from '@app/store/client_page_global_store';
import {ConfigGlobalStore} from '@app/store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '@app/store/config_global_store_test_util';
import {initTestEnvironment} from '@app/testing';

import {newClient, newFlowDescriptor} from '../../lib/models/model_test_util';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';

import {FlowForm} from './flow_form';


initTestEnvironment();

function getSubmit<T>(fixture: ComponentFixture<T>) {
  return fixture.nativeElement.querySelector('button[type=submit]');
}

describe('FlowForm Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let clientPageGlobalStore: ClientPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    clientPageGlobalStore = mockClientPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FlowFormModule,
          ],

          providers: [
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore
            },
          ]
        })
        .compileComponents();
  }));

  it('shows no submit button without selected flow', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeNull();

    clientPageGlobalStore.selectedFlowDescriptorSubject.next(undefined);
    expect(getSubmit(fixture)).toBeNull();
  });

  it('shows submit button when flow is selected', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.selectedFlowDescriptorSubject.next(
        newFlowDescriptor());
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeTruthy();
  });

  it('triggers startFlow on form submit', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.selectedClientSubject.next(newClient());
    clientPageGlobalStore.selectedFlowDescriptorSubject.next(newFlowDescriptor({
      name: 'CollectBrowserHistory',
      defaultArgs: {
        browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
      }
    }));
    clientPageGlobalStore.hasAccessSubject.next(true);
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientPageGlobalStore.startFlow).toHaveBeenCalledWith({
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    });
  });

  it('triggers scheduleFlow on form submit without access', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.selectedClientSubject.next(newClient());
    clientPageGlobalStore.hasAccessSubject.next(false);
    clientPageGlobalStore.selectedFlowDescriptorSubject.next(newFlowDescriptor({
      name: 'CollectBrowserHistory',
      defaultArgs: {
        browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
      }
    }));
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientPageGlobalStore.scheduleFlow).toHaveBeenCalledWith({
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    });
  });

  it('shows errors when flow submit fails', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.selectedClientSubject.next(newClient());
    clientPageGlobalStore.selectedFlowDescriptorSubject.next(
        newFlowDescriptor());
    clientPageGlobalStore.hasAccessSubject.next(true);
    fixture.detectChanges();

    clientPageGlobalStore.startFlowStateSubject.next(
        {state: 'error', error: 'foobazzle rapidly disintegrated'});
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('foobazzle rapidly disintegrated');
  });
});
