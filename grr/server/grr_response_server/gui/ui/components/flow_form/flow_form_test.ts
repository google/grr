import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {FlowFormModule} from '../../components/flow_form/module';
import {Browser} from '../../lib/api/api_interfaces';
import {RequestStatusType} from '../../lib/api/track_request';
import {newClient, newFlowDescriptor} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

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
            RouterTestingModule,
            FlowFormModule,
          ],
          providers: [
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('shows no submit button without selected flow', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeNull();

    clientPageGlobalStore.mockedObservables.selectedFlowDescriptor$.next(null);
    expect(getSubmit(fixture)).toBeNull();
  });

  it('shows submit button when flow is selected', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.selectedFlowDescriptor$.next(
        newFlowDescriptor());
    fixture.detectChanges();

    expect(getSubmit(fixture)).toBeTruthy();
  });

  it('triggers scheduleOrStartFlow on form submit', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.selectedClient$.next(newClient());
    clientPageGlobalStore.mockedObservables.selectedFlowDescriptor$.next(
        newFlowDescriptor({
          name: 'CollectBrowserHistory',
          defaultArgs: {
            browsers: [Browser.CHROME],
          }
        }));
    clientPageGlobalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    getSubmit(fixture).click();
    expect(clientPageGlobalStore.scheduleOrStartFlow).toHaveBeenCalledWith({
      browsers: [Browser.CHROME],
    });
  });

  it('shows errors when flow submit fails', () => {
    const fixture = TestBed.createComponent(FlowForm);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.selectedClient$.next(newClient());
    clientPageGlobalStore.mockedObservables.selectedFlowDescriptor$.next(
        newFlowDescriptor());
    clientPageGlobalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    clientPageGlobalStore.mockedObservables.startFlowStatus$.next({
      status: RequestStatusType.ERROR,
      error: 'foobazzle rapidly disintegrated'
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText)
        .toContain('foobazzle rapidly disintegrated');
  });
});
