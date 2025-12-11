import {
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanRegexClientRuleForemanStringField,
} from '../../lib/api/api_interfaces';
import {
  FriendlyForemanIntegerClientRulePipe,
  FriendlyForemanStringClientRulePipe,
} from './friendly_foreman_client_rule_pipe';

describe('Friendly Foreman Integer Client Rule Name Pipe', () => {
  const pipe = new FriendlyForemanIntegerClientRulePipe();

  it('returns the friendly names for the enum values', () => {
    expect(
      pipe.transform(
        ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
      ),
    ).toEqual('Client Version');

    expect(
      pipe.transform(ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME),
    ).toEqual('Install Time');

    expect(
      pipe.transform(
        ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME,
      ),
    ).toEqual('Last Boot Time');

    expect(
      pipe.transform(ForemanIntegerClientRuleForemanIntegerField.UNSET),
    ).toEqual('Unset');
  });
});

describe('Friendly Foreman String Client Rule Name Pipe', () => {
  const pipe = new FriendlyForemanStringClientRulePipe();

  it('returns the friendly names for the enum values', () => {
    expect(
      pipe.transform(
        ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
      ),
    ).toEqual('Client Description');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.CLIENT_ID),
    ).toEqual('Client ID');

    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.CLIENT_LABELS),
    ).toEqual('Client Labels');

    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.CLIENT_NAME),
    ).toEqual('Client Name');

    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.FQDN),
    ).toEqual('FQDN');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.HOST_IPS),
    ).toEqual('Host IPs');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.KERNEL_VERSION),
    ).toEqual('Kernel Version');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES),
    ).toEqual('Mac Addresses');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.OS_RELEASE),
    ).toEqual('OS Release');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.OS_VERSION),
    ).toEqual('OS Version');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.SYSTEM),
    ).toEqual('System');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.UNSET),
    ).toEqual('Unset');
    expect(
      pipe.transform(ForemanRegexClientRuleForemanStringField.USERNAMES),
    ).toEqual('User Names');
  });
});
