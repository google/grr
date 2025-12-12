import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

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
import {FlowDebugging} from './flow_debugging';
import {FlowDebuggingHarness} from './testing/flow_debugging_harness';

initTestEnvironment();

async function createComponent(flowId: string) {
  const fixture = TestBed.createComponent(FlowDebugging);
  fixture.componentRef.setInput('flowId', flowId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowDebuggingHarness,
  );
  return {fixture, harness};
}

describe('Flow Debugging Component', () => {
  let clientStoreMock: ClientStoreMock;
  let flowStoreMock: FlowStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();
    flowStoreMock = newFlowStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowDebugging, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: FlowStore,
          useValue: flowStoreMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent('1234');
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('loads flow logs when component is created', async () => {
    await createComponent('1234');

    expect(flowStoreMock.fetchFlowLogs).toHaveBeenCalled();
  });

  it('shows flow logs component', async () => {
    const {harness} = await createComponent('1234');

    const flowLogs = await harness.flowLogs();

    expect(flowLogs).toBeDefined();
  });
});
