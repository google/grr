import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowState, FlowType} from '../../../lib/models/flow';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {FlowStore} from '../../../store/flow_store';
import {FlowStoreMock, newFlowStoreMock} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionClientResults} from './fleet_collection_client_results';
import {FleetCollectionClientResultsHarness} from './testing/fleet_collection_client_results_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionClientResults);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionClientResultsHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Client Results Component', () => {
  let flowStoreMock: FlowStoreMock;

  beforeEach(waitForAsync(() => {
    flowStoreMock = newFlowStoreMock();

    TestBed.configureTestingModule({
      imports: [FleetCollectionClientResults],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    })
      .overrideComponent(FleetCollectionClientResults, {
        set: {
          providers: [
            {
              provide: FlowStore,
              useValue: flowStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows correct number of results loaded', async () => {
    flowStoreMock.countLoadedResults = signal(10);
    flowStoreMock.countTotalResults = signal(20);
    const {harness} = await createComponent();

    expect(await harness.getOverviewText()).toContain(
      '10 of 20 results loaded',
    );
  });

  it('shows collection results component', async () => {
    flowStoreMock.flow = signal(
      newFlow({
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        resultCounts: [{type: 'StatEntry', count: 1}],
        state: FlowState.FINISHED,
      }),
    );
    flowStoreMock.flowResultsByPayloadType = signal(
      new Map([
        [
          PayloadType.USER,
          [
            newFlowResult({payloadType: PayloadType.USER}),
            newFlowResult({payloadType: PayloadType.USER}),
          ],
        ],
      ]),
    );
    const {harness} = await createComponent();

    const collectionResults = await harness.collectionResults();
    expect(collectionResults).toBeDefined();
    expect(await collectionResults.users()).not.toBeNull();
  });

  it('shows download button', async () => {
    flowStoreMock.flow = signal(
      newFlow({
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        resultCounts: [{type: 'StatEntry', count: 1}],
        state: FlowState.FINISHED,
      }),
    );
    const {harness} = await createComponent();

    const downloadButton = await harness.downloadButton();
    expect(await downloadButton.hasDownloadButton()).toBeTrue();
  });
});
