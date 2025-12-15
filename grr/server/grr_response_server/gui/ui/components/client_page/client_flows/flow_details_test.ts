import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {ClientStore} from '../../../store/client_store';
import {FlowStore} from '../../../store/flow_store';
import {
  ClientStoreMock,
  FlowStoreMock,
  newClientStoreMock,
  newFlowStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {FlowDetails} from './flow_details';
import {FlowDetailsHarness} from './testing/flow_details_harness';

initTestEnvironment();

async function createComponent(flowId = '1234') {
  const fixture = TestBed.createComponent(FlowDetails);
  fixture.componentRef.setInput('flowId', flowId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowDetailsHarness,
  );
  return {fixture, harness};
}

describe('Flow Details Component', () => {
  let clientStoreMock: ClientStoreMock;
  let flowStoreMock: FlowStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();
    flowStoreMock = newFlowStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FlowDetails,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: FlowStore,
          useValue: flowStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: false},
    })
      .overrideComponent(FlowDetails, {
        set: {
          providers: [
            {
              provide: ClientStore,
              useValue: clientStoreMock,
            },
          ],
        },
      })

      .compileComponents();
  }));

  it('navigation to /results opens FlowResults component in router outlet', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/clients/C.1222/flows/1234/results',
    );

    const {harness} = await createComponent();
    expect(await harness.hasResultsComponent()).toBeTrue();
  }));

  it('navigation to /configuration opens FlowConfiguration component in router outlet', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/clients/C.1222/flows/1234/configuration',
    );

    const {harness} = await createComponent();
    expect(await harness.hasConfigurationComponent()).toBeTrue();
  }));

  it('navigation to /debug opens FlowDebugging component in router outlet', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/clients/C.1222/flows/1234/debug',
    );

    const {harness} = await createComponent();
    expect(await harness.hasDebuggingComponent()).toBeTrue();
  }));

  it('opens results tab by default', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');

    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/clients/C.1222/flows/1234');

    const {harness} = await createComponent();
    expect(await harness.hasResultsComponent()).toBeTrue();
  }));

  it('calls client store to poll flow when initialized', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    await createComponent();
    expect(clientStoreMock.pollFlow).toHaveBeenCalled();
  }));

  it('initializes flow store when initialized', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1222');
    await createComponent('1234');

    expect(flowStoreMock.initialize).toHaveBeenCalledWith('C.1222', '1234');
  }));
});
