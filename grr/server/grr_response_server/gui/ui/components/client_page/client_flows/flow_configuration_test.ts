import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowType} from '../../../lib/models/flow';
import {newFlow} from '../../../lib/models/model_test_util';
import {ClientStore} from '../../../store/client_store';
import {
  ClientStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FlowConfiguration} from './flow_configuration';
import {FlowConfigurationHarness} from './testing/flow_configuration_harness';

initTestEnvironment();

async function createComponent(flowId: string) {
  const fixture = TestBed.createComponent(FlowConfiguration);
  fixture.componentRef.setInput('flowId', flowId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowConfigurationHarness,
  );
  return {fixture, harness};
}

describe('Flow Configuration Component', () => {
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowConfiguration, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent('1234');
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('displays correct flow args form', async () => {
    clientStoreMock.clientId = signal('C.1111');
    clientStoreMock.flowsByFlowId = signal(
      new Map([
        [
          '1234',
          newFlow({
            flowId: '1234',
            flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
            args: {
              'artifact_list': ['artifact1', 'artifact2'],
            },
          }),
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    const flowArgsForm = await harness.flowArgsForm();
    expect(flowArgsForm).toBeDefined();
    expect(await flowArgsForm!.artifactCollectorFlowForm()).toBeDefined();
  });

  it('shows disabled flow args form', async () => {
    clientStoreMock.clientId = signal('C.1111');
    clientStoreMock.flowsByFlowId = signal(
      new Map([
        [
          '1234',
          newFlow({
            flowId: '1234',
            flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
            args: {
              'artifact_list': ['artifact1', 'artifact2'],
            },
          }),
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    const flowArgsForm = await harness.flowArgsForm();
    expect(await flowArgsForm!.isDisabled()).toBeTrue();
  });
});
