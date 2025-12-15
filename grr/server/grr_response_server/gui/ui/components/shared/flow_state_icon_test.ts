import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {Flow, FlowState} from '../../lib/models/flow';
import {newFlow} from '../../lib/models/model_test_util';
import {initTestEnvironment} from '../../testing';
import {FlowStateIcon} from './flow_state_icon';
import {FlowStateIconHarness} from './testing/flow_state_icon_harness';

initTestEnvironment();

async function createComponent(flow: Flow) {
  const fixture = TestBed.createComponent(FlowStateIcon);
  fixture.componentRef.setInput('flow', flow);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FlowStateIconHarness,
  );
  return {fixture, harness};
}

describe('Flow State Icon Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [FlowStateIcon],
    }).compileComponents();
  }));

  it('is created successfully', async () => {
    const {fixture} = await createComponent(newFlow({}));

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance).toBeInstanceOf(FlowStateIcon);
  });

  it('shows running flow state icon', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.RUNNING,
      }),
    );

    expect(await harness.runningIcon()).toBeDefined();
    expect(await harness.finishedIcon()).toBeNull();
    expect(await harness.errorIcon()).toBeNull();
  });

  it('shows finished flow state icon', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.FINISHED,
      }),
    );

    expect(await harness.runningIcon()).toBeNull();
    expect(await harness.finishedIcon()).toBeDefined();
    expect(await harness.errorIcon()).toBeNull();
  });

  it('shows error flow state icon', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.ERROR,
      }),
    );

    expect(await harness.runningIcon()).toBeNull();
    expect(await harness.finishedIcon()).toBeNull();
    expect(await harness.errorIcon()).toBeDefined();
  });

  it('shows no icon if flow state is unset', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.UNSET,
      }),
    );

    expect(await harness.runningIcon()).toBeNull();
    expect(await harness.finishedIcon()).toBeNull();
    expect(await harness.errorIcon()).toBeNull();
  });

  it('shows number of results in flow state icon for running flow', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.RUNNING,
        resultCounts: [
          {
            type: 'foo',
            count: 10,
          },
          {
            type: 'bar',
            count: 20,
          },
        ],
      }),
    );

    expect(await harness.hasBadge()).toBeTrue();
    expect(await harness.badgeText()).toBe('30');
  });

  it('shows number of results in flow state icon for finished flow', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.FINISHED,
        resultCounts: [
          {
            type: 'foo',
            count: 10,
          },
          {
            type: 'bar',
            count: 20,
          },
        ],
      }),
    );

    expect(await harness.hasBadge()).toBeTrue();
    expect(await harness.badgeText()).toBe('30');
  });

  it('does not show number of results in flow state icon if flow returned error', async () => {
    const {harness} = await createComponent(
      newFlow({
        state: FlowState.ERROR,
        resultCounts: [
          {
            type: 'foo',
            count: 10,
          },
        ],
      }),
    );

    expect(await harness.hasBadge()).toBeFalse();
  });
});
