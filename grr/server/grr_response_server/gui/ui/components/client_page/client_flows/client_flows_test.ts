import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatDialog, MatDialogConfig} from '@angular/material/dialog';
import {RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowState, FlowType} from '../../../lib/models/flow';
import {
  newClient,
  newFlow,
  newScheduledFlow,
} from '../../../lib/models/model_test_util';
import {ClientStore} from '../../../store/client_store';
import {
  ClientStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {ClientFlows, FlowFilter} from './client_flows';
import {CreateFlowDialog} from './create_flow_dialog';
import {ClientFlowsHarness} from './testing/client_flows_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientFlows);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientFlowsHarness,
  );
  return {fixture, harness};
}

describe('Client Flows Component', () => {
  let clientStoreMock: ClientStoreMock;
  let mockDialog: jasmine.SpyObj<MatDialog>;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();
    mockDialog = jasmine.createSpyObj<MatDialog>(['open']);

    TestBed.configureTestingModule({
      imports: [
        ClientFlows,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {provide: MatDialog, useValue: mockDialog},
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  }));

  it('does not display "New Flow" button when client is not available', fakeAsync(async () => {
    clientStoreMock.client = signal(null);

    const {harness} = await createComponent();
    expect(await harness.newFlowButton()).toBeNull();
  }));

  it('displays "New Flow" button when client is available', fakeAsync(async () => {
    clientStoreMock.client = signal(newClient({clientId: 'C.1234'}));
    const {harness} = await createComponent();

    expect(await harness.newFlowButton()).toBeDefined();
  }));

  it('opens the new flow dialog when "New Flow" button is clicked', async () => {
    const client = newClient({clientId: 'C.1234'});
    clientStoreMock.client = signal(client);
    const {harness} = await createComponent();

    const newFlowButton = await harness.newFlowButton();
    await newFlowButton!.click();

    const expectedDialogConfig = new MatDialogConfig();
    expectedDialogConfig.data = {
      flowType: undefined,
      flowArgs: undefined,
      onSubmit: jasmine.any(Function),
      client,
    };
    expectedDialogConfig.autoFocus = false;
    expectedDialogConfig.minWidth = '60vw';
    expectedDialogConfig.height = '70vh';

    expect(mockDialog.open).toHaveBeenCalledWith(
      CreateFlowDialog,
      expectedDialogConfig,
    );
  });

  it('can create empty flow list', fakeAsync(async () => {
    clientStoreMock.flows = signal([]);
    tick();
    const {harness} = await createComponent();
    const flowList = await harness.flowList();

    expect(await flowList.getItems()).toHaveSize(0);
  }));

  it('displays complete flow item', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1234',
        name: 'Flow',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        startedAt: new Date('2024-01-01T00:00:00Z'),
        state: FlowState.RUNNING,
        isRobot: true,
      }),
    ]);
    tick();
    const {harness} = await createComponent();
    await harness.selectFilterOption(FlowFilter.ALL_FLOWS);

    const flowListItems = await harness.getFlowListItems();
    expect(flowListItems).toHaveSize(1);

    expect(await harness.getFlowListItemTitle(0)).toContain(
      'Collect a forensic artifact',
    );
    expect(await harness.getFlowListItemText(0)).toContain('f.1234');
    expect(await harness.getFlowListItemText(0)).toContain(
      '2024-01-01 00:00:00 UTC',
    );
    expect(await harness.hasFlowListItemRobotIcon(0)).toBeTrue();
    expect(await harness.hasCopyLinkButton(0)).toBeTrue();
    const flowStateIcon = await harness.getFlowStateIcon(0);
    expect(await flowStateIcon.runningIcon()).not.toBeNull();

    expect(await harness.hasFlowMenuButton(0)).toBeTrue();
    await harness.clickFlowMenuButton(0);
    const flowMenuItems = await harness.getFlowMenuItems(0);
    expect(flowMenuItems).toHaveSize(3);
    expect(await flowMenuItems[0].getText()).toContain('Cancel flow');
    expect(await flowMenuItems[1].getText()).toContain('Duplicate flow');
    expect(await flowMenuItems[2].getText()).toContain(
      'Create a fleet collection',
    );
  }));

  it('opens the create flow dialog when "Duplicate flow" menu item is clicked', fakeAsync(async () => {
    const client = newClient({clientId: 'C.1234'});
    clientStoreMock.client = signal(client);
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1234',
        name: 'Flow',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        args: {
          artifactCollectorFlowArgs: {
            paths: ['/path/to/artifact'],
          },
        },
        startedAt: new Date('2024-01-01T00:00:00Z'),
        state: FlowState.RUNNING,
        isRobot: false,
      }),
    ]);
    const {harness} = await createComponent();

    await harness.clickFlowMenuButton(0);
    await harness.clickDuplicateFlowMenuItem(0);

    const expectedDialogConfig = new MatDialogConfig();
    expectedDialogConfig.data = {
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      flowArgs: {
        artifactCollectorFlowArgs: {
          paths: ['/path/to/artifact'],
        },
      },
      onSubmit: jasmine.any(Function),
      client: newClient({clientId: 'C.1234'}),
    };
    expectedDialogConfig.autoFocus = false;
    expectedDialogConfig.minWidth = '60vw';
    expectedDialogConfig.height = '70vh';

    expect(mockDialog.open).toHaveBeenCalledWith(
      CreateFlowDialog,
      jasmine.objectContaining(expectedDialogConfig),
    );
  }));

  it('displays several flow items', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1234',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      }),
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.5678',
        flowType: FlowType.COLLECT_BROWSER_HISTORY,
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    const flowListItems = await harness.getFlowListItems();
    expect(flowListItems).toHaveSize(2);

    const title0 = await harness.getFlowListItemTitle(0);
    expect(title0).toContain('Collect a forensic artifact');

    const title1 = await harness.getFlowListItemTitle(1);
    expect(title1).toContain('Collect browser history');
  }));

  it('shows user image for non-robot flows', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1234',
        name: 'Flow',
        startedAt: new Date('2024-01-01T00:00:00Z'),
        state: FlowState.RUNNING,
        isRobot: false,
        creator: 'testuser',
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    const flowListItems = await harness.getFlowListItems();
    expect(flowListItems).toHaveSize(1);

    expect(await harness.hasFlowListItemUserImage(0)).toBeTrue();
  }));

  it('shows "Cancel flow" menu item only for RUNNING flows', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1111',
        state: FlowState.FINISHED,
        isRobot: false,
      }),
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.2222',
        state: FlowState.ERROR,
        isRobot: false,
      }),
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.3333',
        startedAt: new Date('2024-01-01T00:00:00Z'),
        state: FlowState.RUNNING,
        isRobot: false,
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    expect(await harness.getFlowListItems()).toHaveSize(3);

    await harness.clickFlowMenuButton(0);
    expect(await harness.hasCancelFlowMenuItem(0)).toBeFalse();
    await harness.clickFlowMenuButton(1);
    expect(await harness.hasCancelFlowMenuItem(1)).toBeFalse();
    await harness.clickFlowMenuButton(2);
    expect(await harness.hasCancelFlowMenuItem(2)).toBeTrue();
  }));

  it('cancels flow when "Cancel flow" menu item is clicked', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1111',
        startedAt: new Date('2024-01-01T00:00:00Z'),
        state: FlowState.RUNNING,
        isRobot: false,
      }),
    ]);
    clientStoreMock.cancelFlow = jasmine.createSpy('cancelFlow');
    tick();
    const {harness} = await createComponent();
    await harness.clickFlowMenuButton(0);
    await harness.clickCancelFlowMenuItem(0);
    expect(clientStoreMock.cancelFlow).toHaveBeenCalledWith('f.1111');
  }));

  it('filters flows by type', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1111',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        isRobot: false,
      }),
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.2222',
        flowType: FlowType.COLLECT_BROWSER_HISTORY,
        isRobot: true,
      }),
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.3333',
        flowType: FlowType.DUMP_PROCESS_MEMORY,
        isRobot: false,
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    // By default all human flows are shown.
    expect(await harness.getFlowListItems()).toHaveSize(2);
    expect(await harness.getFlowListItemTitle(0)).toContain('artifact');
    expect(await harness.getFlowListItemTitle(1)).toContain('process');

    await harness.selectFilterOption(FlowFilter.ALL_ROBOT_FLOWS);
    expect(await harness.getFlowListItems()).toHaveSize(1);
    expect(await harness.getFlowListItemTitle(0)).toContain('browser');

    await harness.selectFilterOption(FlowFilter.ALL_FLOWS);
    expect(await harness.getFlowListItems()).toHaveSize(3);
    expect(await harness.getFlowListItemTitle(0)).toContain('artifact');
    expect(await harness.getFlowListItemTitle(1)).toContain('browser');
    expect(await harness.getFlowListItemTitle(2)).toContain('process');
  }));

  it('expands nested flows', fakeAsync(async () => {
    clientStoreMock.flows = signal([
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1111',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        isRobot: false,
        nestedFlows: [
          newFlow({
            clientId: 'C.1234',
            flowId: 'f.2222',
            flowType: FlowType.COLLECT_BROWSER_HISTORY,
            isRobot: false,
            nestedFlows: [
              newFlow({
                clientId: 'C.1234',
                flowId: 'f.3333',
                flowType: FlowType.DUMP_PROCESS_MEMORY,
                isRobot: false,
              }),
            ],
          }),
        ],
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    expect(await harness.getFlowListItems()).toHaveSize(1);

    // Expand first level of nested flows.
    expect(await harness.hasNestedFlowsButton(0)).toBeTrue();
    await harness.clickNestedFlowsButton(0);
    expect(await harness.getFlowListItems()).toHaveSize(2);
    expect(await harness.getFlowListItemTitle(1)).toContain('browser');

    // Expand second level of nested flows.
    expect(await harness.hasNestedFlowsButton(1)).toBeTrue();
    await harness.clickNestedFlowsButton(1);
    expect(await harness.getFlowListItems()).toHaveSize(3);
    expect(await harness.getFlowListItemTitle(2)).toContain('process');

    expect(await harness.hasNestedFlowsButton(2)).toBeFalse();
    // Collapse nested flows.
    await harness.clickNestedFlowsButton(0);
    expect(await harness.getFlowListItems()).toHaveSize(1);
  }));

  it('can create empty scheduled flow list', fakeAsync(async () => {
    clientStoreMock.flows = signal([]);
    tick();
    const {harness} = await createComponent();
    const scheduledFlowList = await harness.scheduledFlowList();

    expect(await scheduledFlowList.getItems()).toHaveSize(0);
  }));

  it('displays complete scheduled flow item', fakeAsync(async () => {
    clientStoreMock.scheduledFlows = signal([
      newScheduledFlow({
        scheduledFlowId: 'f.1234',
        clientId: 'C.1234',
        creator: 'testuser',
        createTime: new Date('2024-01-01T00:00:00Z'),
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      }),
    ]);
    tick();

    const {harness} = await createComponent();

    const flowListItems = await harness.getScheduledFlowListItems();
    expect(flowListItems).toHaveSize(1);

    expect(await harness.getScheduledFlowListItemTitle(0)).toContain(
      'Scheduled: Collect a forensic artifact',
    );
    expect(await harness.getScheduledFlowListItemText(0)).toContain('f.1234');
    expect(await harness.getScheduledFlowListItemText(0)).toContain(
      '2024-01-01 00:00:00 UTC',
    );
    expect(await harness.hasScheduledFlowListItemUserImage(0)).toBeTrue();
    expect(await harness.hasCopyLinkForScheduledFlowButton(0)).toBeTrue();
    expect(await harness.getPendingApprovalProgressIcon(0)).toBeDefined();
  }));

  it('displays several scheduled flow items', fakeAsync(async () => {
    clientStoreMock.scheduledFlows = signal([
      newScheduledFlow({
        clientId: 'C.1234',
        scheduledFlowId: 'f.1234',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
      }),
      newScheduledFlow({
        clientId: 'C.1234',
        scheduledFlowId: 'f.5678',
        flowType: FlowType.COLLECT_BROWSER_HISTORY,
      }),
    ]);
    tick();
    const {harness} = await createComponent();

    const flowListItems = await harness.getScheduledFlowListItems();
    expect(flowListItems).toHaveSize(2);

    const title0 = await harness.getScheduledFlowListItemTitle(0);
    expect(title0).toContain('Scheduled: Collect a forensic artifact');

    const title1 = await harness.getScheduledFlowListItemTitle(1);
    expect(title1).toContain('Scheduled: Collect browser history');
  }));

  it('displays missing approval component when flow is only scheduled', fakeAsync(async () => {
    clientStoreMock.scheduledFlows = signal([
      newScheduledFlow({
        clientId: 'C.1234567890abcdef',
        scheduledFlowId: 'f.1111',
      }),
    ]);

    const {harness} = await createComponent();
    const flowListItems = await harness.getScheduledFlowListItems();
    await (await flowListItems[0].host()).click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual(
      '/clients/C.1234567890abcdef/flows/scheduled-flow',
    );
  }));
});
