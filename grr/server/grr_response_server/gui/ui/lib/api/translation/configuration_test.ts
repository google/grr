import {initTestEnvironment} from '../../../testing';
import {UiConfig} from '../../models/configuration';
import {OutputPluginType} from '../../models/output_plugin';
import * as apiInterfaces from '../api_interfaces';
import {translateUiConfig} from './configuration';

initTestEnvironment();

describe('Configuration API Translation', () => {
  it('converts all UiConfig fields correctly', () => {
    const api: apiInterfaces.ApiUiConfig = {
      heading: 'foo',
      reportUrl: 'bar',
      helpUrl: 'baz',
      grrVersion: 'qux',
      profileImageUrl: 'quux',
      defaultHuntRunnerArgs: {
        huntName: 'foo',
        description: 'bar',
        clientRuleSet: {
          matchMode: apiInterfaces.ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [
            {
              ruleType: apiInterfaces.ForemanClientRuleType.OS,
              os: {osWindows: true, osLinux: true, osDarwin: true},
            },
          ],
        },
        cpuLimit: '1',
        networkBytesLimit: '2',
        clientLimit: '3',
        crashLimit: '4',
        avgResultsPerClientLimit: '5',
        avgCpuSecondsPerClientLimit: '6',
        avgNetworkBytesPerClientLimit: '7',
        expiryTime: '8',
        clientRate: 0.9,
        crashAlertEmail: 'foo@bar.com',
        outputPlugins: [],
        perClientCpuLimit: '10',
        perClientNetworkLimitBytes: '11',
        originalObject: {
          objectType:
            apiInterfaces.FlowLikeObjectReferenceObjectType.FLOW_REFERENCE,
          flowReference: {
            flowId: '12',
            clientId: '13',
          },
        },
      },
      defaultOutputPlugins: [
        {
          pluginName: 'EmailOutputPlugin',
        },
      ],
      huntConfig: {},
      clientWarnings: {
        rules: [
          {
            withLabels: ['foo', 'bar'],
            message: 'baz',
          },
        ],
      },
      defaultAccessDurationSeconds: '100',
      maxAccessDurationSeconds: '200',
    };
    const result: UiConfig = {
      heading: 'foo',
      reportUrl: 'bar',
      helpUrl: 'baz',
      grrVersion: 'qux',
      profileImageUrl: 'quux',
      defaultHuntRunnerArgs: {
        huntName: 'foo',
        description: 'bar',
        clientRuleSet: {
          matchMode: apiInterfaces.ForemanClientRuleSetMatchMode.MATCH_ALL,
          rules: [
            {
              ruleType: apiInterfaces.ForemanClientRuleType.OS,
              os: {osWindows: true, osLinux: true, osDarwin: true},
            },
          ],
        },
        cpuLimit: '1',
        networkBytesLimit: '2',
        clientLimit: '3',
        crashLimit: '4',
        avgResultsPerClientLimit: '5',
        avgCpuSecondsPerClientLimit: '6',
        avgNetworkBytesPerClientLimit: '7',
        expiryTime: '8',
        clientRate: 0.9,
        crashAlertEmail: 'foo@bar.com',
        outputPlugins: [],
        perClientCpuLimit: '10',
        perClientNetworkLimitBytes: '11',
        originalObject: {
          objectType:
            apiInterfaces.FlowLikeObjectReferenceObjectType.FLOW_REFERENCE,
          flowReference: {
            flowId: '12',
            clientId: '13',
          },
        },
      },
      defaultOutputPlugins: [
        {
          pluginType: OutputPluginType.EMAIL,
          args: undefined,
        },
      ],
      safetyLimits: {
        clientRate: 0.9,
        clientLimit: BigInt(3),
        crashLimit: BigInt(4),
        avgResultsPerClientLimit: BigInt(5),
        avgCpuSecondsPerClientLimit: BigInt(6),
        avgNetworkBytesPerClientLimit: BigInt(7),
        expiryTime: BigInt(8),
        perClientCpuLimit: BigInt(10),
        perClientNetworkBytesLimit: BigInt(11),
      },
      huntConfig: {},
      clientWarnings: {
        rules: [
          {
            withLabels: ['foo', 'bar'],
            message: 'baz',
          },
        ],
      },
      defaultAccessDurationSeconds: 100,
      maxAccessDurationSeconds: 200,
    };
    expect(translateUiConfig(api)).toEqual(result);
  });
});
