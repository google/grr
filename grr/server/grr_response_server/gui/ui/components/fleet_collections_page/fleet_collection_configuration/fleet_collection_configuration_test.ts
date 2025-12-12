import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {MatDialog} from '@angular/material/dialog';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {FlowType} from '../../../lib/models/flow';
import {HuntState} from '../../../lib/models/hunt';
import {newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {FleetCollectionsStore} from '../../../store/fleet_collections_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionsStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES, FLEET_COLLECTION_ROUTES} from '../../app/routing';
import {FleetCollectionConfiguration} from './fleet_collection_configuration';
import {ModifyFleetCollectionDialog} from './modify_fleet_collection_dialog';
import {FleetCollectionConfigurationHarness} from './testing/fleet_collection_configuration_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionConfiguration);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionConfigurationHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Configuration Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;
  let mockDialog: jasmine.SpyObj<MatDialog>;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    mockDialog = jasmine.createSpyObj<MatDialog>(['open']);

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionConfiguration,
        RouterModule.forRoot([...CLIENT_ROUTES, ...FLEET_COLLECTION_ROUTES], {
          bindToComponentInputs: true,
        }),
        NoopAnimationsModule,
      ],
      providers: [
        {provide: MatDialog, useValue: mockDialog},
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
        },
        {
          provide: FleetCollectionsStore,
          useValue: newFleetCollectionsStoreMock(),
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  }));

  it('shows fleet collection state chip', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
        state: HuntState.RUNNING,
      }),
    );
    const {harness} = await createComponent();

    const fleetCollectionStateChip = await harness.fleetCollectionStateChip();
    expect(await fleetCollectionStateChip.getChipText()).toContain('Running');
  }));

  describe('Start Fleet Collection button', () => {
    it('is disabled when user has no access', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeTrue();
      const accessTooltip = await harness.accessTooltip();
      await accessTooltip.show();
      expect(await accessTooltip.getTooltipText()).toContain(
        'Get approval to change the configuration of this Fleet Collection.',
      );
    }));

    it('is enabled when user has access and fleet collection is not in NOT_STARTED state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.NOT_STARTED,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeFalse();
    }));

    it('is disabled when user has access and fleet collection is in RUNNING state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.startFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only start a Fleet Collection from paused state.',
      );
    }));

    it('is disabled when user has access and fleet collection is in REACHED_CLIENT_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_CLIENT_LIMIT,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.startFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only start a Fleet Collection from paused state.',
      );
    }));

    it('is disabled when user has access and fleet collection is in CANCELLED state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.CANCELLED,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.startFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only start a Fleet Collection from paused state.',
      );
    }));

    it('is disabled when user has access and fleet collection is in REACHED_TIME_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_TIME_LIMIT,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      expect(await startFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.startFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only start a Fleet Collection from paused state.',
      );
    }));

    it('shows no tooltip when user has access and fleet collection is in NOT_STARTED state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.NOT_STARTED,
        }),
      );
      const {harness} = await createComponent();

      const accessTooltip = await harness.accessTooltip();
      await accessTooltip.show();
      expect(await accessTooltip.getTooltipText()).toBe('');
      const startFleetCollectionTooltip =
        await harness.startFleetCollectionTooltip();
      await startFleetCollectionTooltip.show();
      expect(await startFleetCollectionTooltip.getTooltipText()).toBe('');
    }));

    it('calls the store when clicked', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.NOT_STARTED,
        }),
      );
      const {harness} = await createComponent();

      const startFleetCollectionButton =
        await harness.startFleetCollectionButton();
      await startFleetCollectionButton.click();

      expect(fleetCollectionStoreMock.startFleetCollection).toHaveBeenCalled();
    }));
  });

  describe('Modify Rollout Parameters button', () => {
    it('is disabled when fleet collection is not defined', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(null);
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeTrue();
    }));

    it('is enabled when fleet collection is in NOT_STARTED state', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.NOT_STARTED,
          safetyLimits: newSafetyLimits({}),
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeFalse();
      const tooltip = await harness.modifyRolloutParametersTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toBe('');
    }));

    it('is enabled when fleet collection is in RUNNING state', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
          safetyLimits: newSafetyLimits({}),
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeFalse();
      const tooltip = await harness.modifyRolloutParametersTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toBe('');
    }));

    it('is enabled when fleet collection is in REACHED_CLIENT_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_CLIENT_LIMIT,
          safetyLimits: newSafetyLimits({}),
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeFalse();
      const tooltip = await harness.modifyRolloutParametersTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toBe('');
    }));

    it('is disabled when fleet collection is in CANCELLED state', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.CANCELLED,
          safetyLimits: newSafetyLimits({}),
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeTrue();
      const tooltip = await harness.modifyRolloutParametersTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toBe(
        'Can only modify rollout parameters of an ongoing Fleet Collection.',
      );
    }));

    it('is disabled when fleet collection is in REACHED_TIME_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_TIME_LIMIT,
          safetyLimits: newSafetyLimits({}),
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      expect(await modifyButton.isDisabled()).toBeTrue();
      const tooltip = await harness.modifyRolloutParametersTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toBe(
        'Can only modify rollout parameters of an ongoing Fleet Collection.',
      );
    }));

    it('opens the modify fleet collection dialog and passes the current safety limits when clicked', fakeAsync(async () => {
      const safetyLimits = newSafetyLimits({
        clientLimit: BigInt(1234),
        clientRate: 567,
      });
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
          safetyLimits,
        }),
      );
      const {harness} = await createComponent();

      const modifyButton = await harness.modifyRolloutParametersButton();
      await modifyButton.click();

      expect(mockDialog.open).toHaveBeenCalledWith(
        ModifyFleetCollectionDialog,
        {
          data: {
            currentSafetyLimits: safetyLimits,
            onSubmit: fleetCollectionStoreMock.updateFleetCollection,
          },
          minWidth: '60vw',
          height: '70vh',
        },
      );
    }));
  });

  describe('Cancel Fleet Collection button', () => {
    it('is disabled when user has no access', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(false);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeTrue();
      const accessTooltip = await harness.accessTooltip();
      await accessTooltip.show();
      expect(await accessTooltip.getTooltipText()).toContain(
        'Get approval to change the configuration of this Fleet Collection.',
      );
    }));

    it('is enabled when user has access and fleet collection is in NOT_STARTED state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.NOT_STARTED,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeFalse();
    }));

    it('is enabled when user has access and fleet collection is in RUNNING state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeFalse();
    }));

    it('is enabled when user has access and fleet collection is in REACHED_CLIENT_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_CLIENT_LIMIT,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeFalse();
    }));

    it('is disabled when user has access and fleet collection is in REACHED_TIME_LIMIT state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.REACHED_TIME_LIMIT,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.cancelFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only cancel a Fleet Collection an ongoing Fleet Collection.',
      );
    }));

    it('is disabled when user has access and fleet collection is in CANCELLED state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.CANCELLED,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      expect(await cancelFleetCollectionButton.isDisabled()).toBeTrue();
      const tooltip = await harness.cancelFleetCollectionTooltip();
      await tooltip.show();
      expect(await tooltip.getTooltipText()).toContain(
        'Can only cancel a Fleet Collection an ongoing Fleet Collection.',
      );
    }));

    it('shows no tooltip when user has access and fleet collection is in RUNNING state', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const accessTooltip = await harness.accessTooltip();
      await accessTooltip.show();
      expect(await accessTooltip.getTooltipText()).toBe('');
      const cancelFleetCollectionTooltip =
        await harness.cancelFleetCollectionTooltip();
      await cancelFleetCollectionTooltip.show();
      expect(await cancelFleetCollectionTooltip.getTooltipText()).toBe('');
    }));

    it('calls the store when clicked', fakeAsync(async () => {
      fleetCollectionStoreMock.hasAccess = signal(true);
      fleetCollectionStoreMock.fleetCollection = signal(
        newHunt({
          huntId: '1234',
          state: HuntState.RUNNING,
        }),
      );
      const {harness} = await createComponent();

      const cancelFleetCollectionButton =
        await harness.cancelFleetCollectionButton();
      await cancelFleetCollectionButton.click();

      expect(fleetCollectionStoreMock.cancelFleetCollection).toHaveBeenCalled();
    }));
  });

  it('shows gerneral information', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
        description: 'Test description',
        creator: 'test-creator',
        isRobot: false,
        flowType: FlowType.CLIENT_FILE_FINDER,
        created: new Date(111111),
        initStartTime: new Date(222222),
        lastStartTime: new Date(333333),
        flowReference: {clientId: 'C.1234567890', flowId: 'ABCDEF'},
      }),
    );
    const {harness} = await createComponent();

    const generalInfoTable = await harness.generalInfoTable();
    expect(await generalInfoTable.text()).toContain('Description');
    expect(await generalInfoTable.text()).toContain('Test description');
    expect(await generalInfoTable.text()).toContain('Flow Type');
    expect(await generalInfoTable.text()).toContain('Client file finder');
    expect(await generalInfoTable.text()).toContain('Creator');
    const creator = await harness.creator();
    expect(await creator.getUsername()).toBe('test-creator');
    expect(await generalInfoTable.text()).toContain('Created');
    expect(await generalInfoTable.text()).toContain('1970-01-01 00:01:51 UTC');
    expect(await generalInfoTable.text()).toContain('Initial start time');
    expect(await generalInfoTable.text()).toContain('1970-01-01 00:03:42 UTC');
    expect(await generalInfoTable.text()).toContain('Last started');
    expect(await generalInfoTable.text()).toContain('1970-01-01 00:05:33 UTC');
    expect(await generalInfoTable.text()).toContain('Source Flow');
    expect(await generalInfoTable.text()).toContain('ABCDEF');
  }));

  it('clicking flow id link navigates to the flow page', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
        flowReference: {clientId: 'C.1234567890', flowId: 'ABCDEF'},
      }),
    );
    const {harness} = await createComponent();

    const flowIdLink = await harness.flowIdLink();
    await flowIdLink!.click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual(
      '/clients/C.1234567890/flows/ABCDEF/results',
    );
  }));

  it('clicking fleet collection link navigates to the fleet collection page', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
        huntReference: {huntId: '5678'},
      }),
    );
    const {harness} = await createComponent();

    const fleetCollectionLink = await harness.fleetCollectionLink();
    await fleetCollectionLink!.click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/fleet-collections/5678/results');
  }));

  it('shows flow args form', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
        flowName: 'TestFlow',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        flowArgs: {},
      }),
    );
    const {harness} = await createComponent();

    const flowArgsForm = await harness.flowArgsForm();
    expect(await flowArgsForm.artifactCollectorFlowForm()).toBeDefined();
  }));

  it('shows fleet collection arguments', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollection = signal(
      newHunt({
        huntId: '1234',
      }),
    );
    const {harness} = await createComponent();

    const fleetCollectionArguments = await harness.fleetCollectionArguments();
    expect(fleetCollectionArguments).toBeTruthy();
  }));
});
