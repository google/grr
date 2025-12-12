import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
  ForemanLabelClientRuleMatchMode,
  ForemanRegexClientRuleForemanStringField,
} from '../../../lib/api/api_interfaces';
import {Hunt} from '../../../lib/models/hunt';
import {
  newClientRuleSet,
  newHunt,
  newSafetyLimits,
} from '../../../lib/models/model_test_util';
import {OutputPluginType} from '../../../lib/models/output_plugin';
import {GlobalStore} from '../../../store/global_store';
import {newGlobalStoreMock} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionArguments} from './fleet_collection_arguments';
import {FleetCollectionArgumentsHarness} from './testing/fleet_collection_arguments_harness';

initTestEnvironment();

async function createComponent(fleetCollection: Hunt) {
  const fixture = TestBed.createComponent(FleetCollectionArguments);
  fixture.componentRef.setInput('fleetCollection', fleetCollection);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionArgumentsHarness,
  );
  return {fixture, harness};
}

describe('Fleet Collection Arguments Component', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, FleetCollectionArguments],
      providers: [
        {
          provide: GlobalStore,
          useValue: newGlobalStoreMock(),
        },
      ],
    }).compileComponents();
  });

  it('is created', async () => {
    const {fixture} = await createComponent(newHunt({}));

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('displays all sections correctly', async () => {
    const {harness} = await createComponent(
      newHunt({
        clientRuleSet: newClientRuleSet({
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,
          rules: [
            {
              ruleType: ForemanClientRuleType.OS,
              os: {osWindows: true, osLinux: true, osDarwin: false},
            },
            {
              ruleType: ForemanClientRuleType.LABEL,
              label: {
                labelNames: ['foo', 'bar'],
                matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY,
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
                attributeRegex: 'I am a regex - .*',
                field:
                  ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
              },
            },
          ],
        }),
        safetyLimits: newSafetyLimits({
          clientRate: 200,
          clientLimit: BigInt(0),
          avgResultsPerClientLimit: BigInt(20),
          avgCpuSecondsPerClientLimit: BigInt(40),
          avgNetworkBytesPerClientLimit: BigInt(80),
          perClientCpuLimit: BigInt(60 * 2),
          perClientNetworkBytesLimit: BigInt(60),
          expiryTime: BigInt(60 * 60 * 24 * 2), // 2 days
        }),
      }),
    );
    const text = await harness.getTextContent();

    expect(text).toContain('match any (or)');

    expect(text).toContain('Operating System:');
    expect(text).toContain('Windows');
    expect(text).toContain('Linux');
    expect(text).not.toContain('Darwin');

    expect(text).toContain('Label:');
    expect(text).toContain('match any:');
    expect(text).toContain('foo, bar');

    expect(text).toContain('Value:');
    expect(text).toContain('Client Version');
    expect(text).toContain('> 1337');

    expect(text).toContain('Regex:');
    expect(text).toContain('Client Description');
    expect(text).toContain('I am a regex - .*');

    expect(text).toContain('Defined Parameters');
    expect(text).toContain('Rollout speed:');
    expect(text).toContain('200 clients/min (standard rollout speed)');
    expect(text).toContain('Run On:');
    expect(text).toContain('All matching clients');
    expect(text).toContain('Active for:');
    expect(text).toContain('2 days');

    expect(text).toContain('Stop fleet collection if...');
    expect(text).toContain('Crash Limit:');
    expect(text).toContain('55 clients');
    expect(text).toContain('Average results per client:');
    expect(text).toContain('20');
    expect(text).toContain('Average CPU (per client):');
    expect(text).toContain('40 s');
    expect(text).toContain('Average network usage (per client):');
    expect(text).toContain('80 B');

    expect(text).toContain('Stop flow collection if...');
    expect(text).toContain('CPU limit per client:');
    expect(text).toContain('2 minutes');
    expect(text).not.toContain('Unlimited');
    expect(text).toContain('Network Limit per client:');
    expect(text).toContain('60 B');
    expect(text).not.toContain('Unlimited');
  });

  it('displays unlimited per client network bytes limit', async () => {
    const {harness} = await createComponent(
      newHunt({
        safetyLimits: newSafetyLimits({
          perClientNetworkBytesLimit: BigInt(0),
        }),
      }),
    );
    const text = await harness.getTextContent();

    expect(text).toContain('Network Limit per client: Unlimited');
  });

  it('displays unlimited per client CPU limit', async () => {
    const {harness} = await createComponent(
      newHunt({
        safetyLimits: newSafetyLimits({
          perClientCpuLimit: BigInt(0),
        }),
      }),
    );
    const text = await harness.getTextContent();

    expect(text).toContain('CPU limit per client: Unlimited');
  });

  it('displays default match mode as "match all (and)" correctly', async () => {
    const {harness} = await createComponent(
      newHunt({
        clientRuleSet: newClientRuleSet({
          matchMode: undefined,
        }),
      }),
    );

    const text = await harness.getTextContent();
    expect(text).toContain('Selected clients – match all (and)');
  });

  it('displays output plugins form', async () => {
    const {harness} = await createComponent(
      newHunt({
        outputPlugins: [
          {
            pluginType: OutputPluginType.EMAIL,
            args: {
              'emailAddress': 'test@example.com',
            },
          },
        ],
      }),
    );

    const outputPluginsForm = await harness.outputPluginsForm();
    expect(outputPluginsForm).toBeDefined();
    expect(await outputPluginsForm!.isDisabled()).toBeTrue();
    expect(await outputPluginsForm!.emailOutputPluginForms()).toHaveSize(1);
  });
});
