import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
  ForemanLabelClientRuleMatchMode,
  ForemanRegexClientRuleForemanStringField,
} from '../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_test_util';
import {FlowState, FlowType} from '../../lib/models/flow';
import {HuntState} from '../../lib/models/hunt';
import {
  newFlow,
  newGrrUser,
  newHunt,
  newSafetyLimits,
} from '../../lib/models/model_test_util';
import {OutputPluginType} from '../../lib/models/output_plugin';
import {GlobalStore} from '../../store/global_store';
import {NewFleetCollectionStore} from '../../store/new_fleet_collection_store';
import {
  GlobalStoreMock,
  NewFleetCollectionStoreMock,
  newGlobalStoreMock,
  newNewFleetCollectionStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {FLEET_COLLECTION_ROUTES} from '../app/routing';
import {NewFleetCollection} from './new_fleet_collection';
import {NewFleetCollectionHarness} from './testing/new_fleet_collection_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(NewFleetCollection);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    NewFleetCollectionHarness,
  );

  return {fixture, harness};
}

describe('New Fleet Collection Component', () => {
  let newFleetCollectionStoreMock: NewFleetCollectionStoreMock;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    newFleetCollectionStoreMock = newNewFleetCollectionStoreMock();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        NewFleetCollection,
        NoopAnimationsModule,
        RouterModule.forRoot(FLEET_COLLECTION_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    })
      .overrideComponent(NewFleetCollection, {
        set: {
          providers: [
            {
              provide: NewFleetCollectionStore,
              useValue: newFleetCollectionStoreMock,
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

  it('initializes the store with the router query params of a flow', async () => {
    const {fixture} = await createComponent();
    await TestBed.inject(Router).navigate([], {
      queryParams: {'clientId': 'C.1234', 'flowId': 'f.1234'},
    });
    fixture.detectChanges();

    expect(newFleetCollectionStoreMock.initialize).toHaveBeenCalledWith(
      undefined,
      {clientId: 'C.1234', flowId: 'f.1234'},
    );
  });

  it('initializes the store with the router query params of a fleet collection', async () => {
    const {fixture} = await createComponent();
    await TestBed.inject(Router).navigate([], {
      queryParams: {'fleetCollectionId': 'H.1234'},
    });
    fixture.detectChanges();

    expect(newFleetCollectionStoreMock.initialize).toHaveBeenCalledWith(
      {huntId: 'H.1234'},
      undefined,
    );
  });

  it('shows an error message if no origin flow/fleet collection ref is set', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal(undefined);
    newFleetCollectionStoreMock.originalFlowRef = signal(undefined);

    const {harness} = await createComponent();

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).not.toBeNull();
    expect(await errorMessage!.getMessage()).toBe(
      'The fleet collection MUST be created from an existing fleet collection or flow. Specify the origin fleet collection or flow using the URL parameters.',
    );
  });

  it('shows an error message if the user does not have access to the flow type', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal(undefined);
    newFleetCollectionStoreMock.originalFlowRef = signal({
      clientId: 'C.1234',
      flowId: 'f.1234',
    });
    newFleetCollectionStoreMock.flowType = signal(FlowType.EXECUTE_PYTHON_HACK);
    globalStoreMock.currentUser = signal(
      newGrrUser({
        isAdmin: false,
      }),
    );
    const {harness} = await createComponent();

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).not.toBeNull();
    expect(await errorMessage!.getMessage()).toContain(
      'No permission to create this fleet collection.',
    );
  });

  it('does not show an error message if origin flow on client is provided', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal(undefined);
    newFleetCollectionStoreMock.originalFlowRef = signal({
      clientId: 'C.1234',
      flowId: 'f.1234',
    });

    const {harness} = await createComponent();

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).toBeNull();
  });

  it('does not show an error message if origin fleet collection is provided and the user is an admin', async () => {
    globalStoreMock.currentUser = signal(
      newGrrUser({
        isAdmin: true,
      }),
    );
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    newFleetCollectionStoreMock.originalFlowRef = signal(undefined);

    const {harness} = await createComponent();

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).toBeNull();
  });

  it('shows origin fleet collection', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    newFleetCollectionStoreMock.originalFleetCollection = signal(
      newHunt({
        huntId: 'H.1234',
        description: 'Test Fleet Collection',
        state: HuntState.RUNNING,
        stateReason: undefined,
        stateComment: '',
        clientsWithResultsCount: BigInt(0),
      }),
    );
    const {harness} = await createComponent();

    const sourceSection = await harness.sourceSection();
    expect(sourceSection).not.toBeNull();
    const sourcesSectionText = await sourceSection!.text();
    expect(sourcesSectionText).toContain('Copy from Fleet Collection:');
    expect(sourcesSectionText).toContain('H.1234');
    const fleetCollectionStateChip = await harness.fleetCollectionStateChip();
    expect(fleetCollectionStateChip).not.toBeNull();
    expect(await fleetCollectionStateChip!.getChipText()).toContain('Running');
  });

  it('shows origin flow', async () => {
    newFleetCollectionStoreMock.originalFlowRef = signal({
      clientId: 'C.1234',
      flowId: 'f.1234',
    });
    newFleetCollectionStoreMock.originalFlow = signal(
      newFlow({
        clientId: 'C.1234',
        flowId: 'f.1234',
        flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
        state: FlowState.RUNNING,
      }),
    );
    const {harness} = await createComponent();

    const sourceSection = await harness.sourceSection();
    expect(sourceSection).not.toBeNull();
    const sourcesSectionText = await sourceSection!.text();
    expect(sourcesSectionText).toContain('Created from flow:');
    expect(sourcesSectionText).toContain('f.1234');
    const flowStateIcon = await harness.flowStateIcon();
    expect(flowStateIcon).not.toBeNull();
    expect(await flowStateIcon!.runningIcon()).not.toBeNull();
  });

  it('shows the disabled flow arguments form', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    newFleetCollectionStoreMock.flowArgs = signal({
      test_arg: 'test_value',
    });
    newFleetCollectionStoreMock.flowType = signal(
      FlowType.ARTIFACT_COLLECTOR_FLOW,
    );
    const {harness} = await createComponent();

    const flowArgsForm = await harness.flowArgsForm();
    expect(flowArgsForm).not.toBeNull();
    expect(await flowArgsForm!.artifactCollectorFlowForm()).not.toBeNull();
    expect(await flowArgsForm!.isDisabled()).toBeTrue();
  });

  it('shows output plugins form', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    const {harness} = await createComponent();

    expect(await harness.outputPluginsForm()).toBeDefined();
  });

  it('shows rollout form', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    const {harness} = await createComponent();

    expect(await harness.rolloutForm()).toBeDefined();
  });

  it('shows clients form', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    const {harness} = await createComponent();

    expect(await harness.clientsForm()).toBeDefined();
  });

  it('can copy a fleet collection', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    newFleetCollectionStoreMock.originalFleetCollection = signal(
      newHunt({
        huntId: 'H.1234',
        description: 'Test Fleet Collection',
        safetyLimits: newSafetyLimits({
          clientRate: 1,
          clientLimit: BigInt(2),
          expiryTime: BigInt(3),
          crashLimit: BigInt(4),
          avgResultsPerClientLimit: BigInt(5),
          avgCpuSecondsPerClientLimit: BigInt(6),
          avgNetworkBytesPerClientLimit: BigInt(7),
          perClientCpuLimit: BigInt(8),
          perClientNetworkBytesLimit: BigInt(9),
        }),
        outputPlugins: [
          {
            pluginType: OutputPluginType.EMAIL,
            args: {
              emailAddress: 'test@example.com',
            },
          },
        ],
        clientRuleSet: {
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [
            {
              ruleType: ForemanClientRuleType.LABEL,
              label: {
                labelNames: ['test_label'],
                matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
              },
            },
            {
              ruleType: ForemanClientRuleType.INTEGER,
              integer: {
                operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
                value: '1337',
                field:
                  ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
              },
            },
            {
              ruleType: ForemanClientRuleType.REGEX,
              regex: {
                attributeRegex: 'test_regex',
                field: ForemanRegexClientRuleForemanStringField.CLIENT_LABELS,
              },
            },
          ],
        },
      }),
    );
    const {harness} = await createComponent();

    const titleInput = await harness.titleInput();
    await titleInput.setValue('Test Fleet Collection');
    const createFleetCollectionButton =
      await harness.createFleetCollectionButton();
    await createFleetCollectionButton.click();

    expect(
      newFleetCollectionStoreMock.createFleetCollection,
    ).toHaveBeenCalledWith(
      'Test Fleet Collection',
      {
        clientRate: 1,
        clientLimit: BigInt(2),
        expiryTime: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        perClientCpuLimit: BigInt(8),
        perClientNetworkBytesLimit: BigInt(9),
      },
      {
        matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
        rules: [
          {
            ruleType: ForemanClientRuleType.LABEL,
            label: {
              labelNames: ['test_label'],
              matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
            },
          },
          {
            ruleType: ForemanClientRuleType.INTEGER,
            integer: {
              operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
              value: '1337',
              field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
            },
          },
          {
            ruleType: ForemanClientRuleType.REGEX,
            regex: {
              attributeRegex: 'test_regex',
              field: ForemanRegexClientRuleForemanStringField.CLIENT_LABELS,
            },
          },
        ],
      },
      [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            emailAddress: 'test@example.com',
          },
        },
      ],
    );
  });

  it('uses default values from the uiConfig when creating a fleet collection from a flow', async () => {
    globalStoreMock.outputPluginDescriptors = signal([
      {
        pluginType: OutputPluginType.EMAIL,
        friendlyName: 'Email Output Plugin',
        description: '',
      },
    ]);
    globalStoreMock.uiConfig = signal({
      safetyLimits: newSafetyLimits({
        clientRate: 1,
        clientLimit: BigInt(2),
        expiryTime: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        perClientCpuLimit: BigInt(8),
        perClientNetworkBytesLimit: BigInt(9),
      }),
      defaultOutputPlugins: [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            emailAddress: 'test@example.com',
          },
        },
      ],
    });
    newFleetCollectionStoreMock.originalFlowRef = signal({
      flowId: '1234',
      clientId: 'C.1234',
    });
    const {harness} = await createComponent();
    const titleInput = await harness.titleInput();
    await titleInput.setValue('Test Fleet Collection');
    const createFleetCollectionButton =
      await harness.createFleetCollectionButton();
    await createFleetCollectionButton.click();

    expect(
      newFleetCollectionStoreMock.createFleetCollection,
    ).toHaveBeenCalledWith(
      'Test Fleet Collection',
      {
        clientRate: 1,
        clientLimit: BigInt(2),
        expiryTime: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        perClientCpuLimit: BigInt(8),
        perClientNetworkBytesLimit: BigInt(9),
      },
      {
        matchMode: 'MATCH_ALL',
        rules: [
          {
            ruleType: 'OS',
            os: {osWindows: false, osDarwin: false, osLinux: false},
          },
        ],
      },
      [
        {
          pluginType: OutputPluginType.EMAIL,
          args: {
            emailAddress: 'test@example.com',
          },
        },
      ],
    );
  });

  it('shows an error if the fleet collection name is empty', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    const {harness} = await createComponent();

    const titleInput = await harness.titleInput();
    await titleInput.setValue('');
    await titleInput.blur();

    const titleFormField = await harness.titleFormField();
    expect(await titleFormField.hasErrors()).toBeTrue();
    expect(await titleFormField.getTextErrors()).toEqual([
      'Input is required.',
    ]);
  });

  it('disables the create button if the fleet collection name is empty', async () => {
    newFleetCollectionStoreMock.originalFleetCollectionRef = signal({
      huntId: 'H.1234',
    });
    const {harness} = await createComponent();

    const titleInput = await harness.titleInput();
    await titleInput.setValue('');
    await titleInput.blur();

    const createFleetCollectionButton =
      await harness.createFleetCollectionButton();
    expect(await createFleetCollectionButton.isDisabled()).toBeTrue();
  });

  it('disables the create button if the fleet collection was already created', async () => {
    newFleetCollectionStoreMock.originalFlowRef = signal({
      flowId: 'f.1234',
      clientId: 'C.1234',
    });
    globalStoreMock.uiConfig = signal({
      safetyLimits: newSafetyLimits({}),
      defaultOutputPlugins: [],
    });
    const {harness} = await createComponent();

    const createFleetCollectionButton =
      await harness.createFleetCollectionButton();
    await createFleetCollectionButton.click();

    expect(await createFleetCollectionButton.isDisabled()).toBeTrue();
  });
});
