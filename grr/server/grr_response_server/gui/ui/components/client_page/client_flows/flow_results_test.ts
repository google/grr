import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newFlow, newFlowResult} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {ClientStore} from '../../../store/client_store';
import {
  ClientStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FlowResults} from './flow_results';
import {FlowResultsHarness} from './testing/flow_results_harness';

initTestEnvironment();

async function createComponent(flowId: string) {
  const fixture = TestBed.createComponent(FlowResults);
  fixture.componentRef.setInput('flowId', flowId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowResultsHarness,
  );
  return {fixture, harness};
}

describe('Flow Results Component', () => {
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();

    TestBed.configureTestingModule({
      imports: [FlowResults, NoopAnimationsModule],
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

  it('shows error description if flow has error', async () => {
    clientStoreMock.flowsByFlowId = signal(
      new Map([
        [
          '1234',
          newFlow({
            flowId: '1234',
            errorDescription: 'Flow failed',
          }),
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).not.toBeNull();
    expect(await errorMessage!.getMessage()).toBe('Flow failed');
  });

  it('does not show error description if flow has no error', async () => {
    clientStoreMock.flowsByFlowId = signal(
      new Map([
        [
          '1234',
          newFlow({
            flowId: '1234',
          }),
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).toBeNull();
  });

  it('shows `Load more` button if there are more results to load', async () => {
    clientStoreMock.flowResultsByFlowId = signal(
      new Map([
        [
          '1234',
          {
            flowResultsByPayloadType: new Map(),
            countLoaded: 1,
            totalCount: 2,
          },
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    expect(await harness.hasLoadMoreButton()).toBeTrue();
  });

  it('does not show `Load more` button if there are no more results to load', async () => {
    clientStoreMock.flowResultsByFlowId = signal(
      new Map([
        [
          '1234',
          {
            flowResultsByPayloadType: new Map(),
            countLoaded: 1,
            totalCount: 1,
          },
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    expect(await harness.hasLoadMoreButton()).toBeFalse();
  });

  it('shows collection results component', async () => {
    clientStoreMock.flowResultsByFlowId = signal(
      new Map([
        [
          '1234',
          {
            flowResultsByPayloadType: new Map([
              [PayloadType.USER, [newFlowResult({})]],
              [
                PayloadType.COLLECT_BROWSER_HISTORY_RESULT,
                [newFlowResult({}), newFlowResult({})],
              ],
            ]),
            countLoaded: 1,
            totalCount: 1,
          },
        ],
      ]),
    );
    const {harness} = await createComponent('1234');

    expect(await harness.collectionResults()).toBeDefined();
    const collectionResults = await harness.collectionResults();
    expect(await collectionResults!.users()).toBeDefined();
    expect(await collectionResults!.statEntryResults()).toBeDefined();
  });
});
