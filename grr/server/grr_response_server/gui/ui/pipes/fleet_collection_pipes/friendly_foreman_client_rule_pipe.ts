import {Pipe, PipeTransform} from '@angular/core';

import {
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanRegexClientRuleForemanStringField,
} from '../../lib/api/api_interfaces';
import {checkExhaustive} from '../../lib/utils';

/**
 * Pipe that returns a friendly name for a ForemanIntegerClientRuleForemanIntegerField.
 */
@Pipe({name: 'friendlyForemanIntegerClientRule', standalone: true, pure: true})
export class FriendlyForemanIntegerClientRulePipe implements PipeTransform {
  transform(ruleType: ForemanIntegerClientRuleForemanIntegerField): string {
    switch (ruleType) {
      case ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION:
        return 'Client Version';
      case ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME:
        return 'Install Time';
      case ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME:
        return 'Last Boot Time';
      case ForemanIntegerClientRuleForemanIntegerField.UNSET:
        return 'Unset';
      default:
        checkExhaustive(ruleType);
    }
  }
}

/**
 * Pipe that returns a friendly name for a ForemanRegexClientRuleForemanStringField.
 */
@Pipe({name: 'friendlyForemanStringClientRule', standalone: true, pure: true})
export class FriendlyForemanStringClientRulePipe implements PipeTransform {
  transform(ruleType: ForemanRegexClientRuleForemanStringField): string {
    switch (ruleType) {
      case ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION:
        return 'Client Description';
      case ForemanRegexClientRuleForemanStringField.CLIENT_ID:
        return 'Client ID';
      case ForemanRegexClientRuleForemanStringField.CLIENT_LABELS:
        return 'Client Labels';
      case ForemanRegexClientRuleForemanStringField.CLIENT_NAME:
        return 'Client Name';
      case ForemanRegexClientRuleForemanStringField.FQDN:
        return 'FQDN';
      case ForemanRegexClientRuleForemanStringField.HOST_IPS:
        return 'Host IPs';
      case ForemanRegexClientRuleForemanStringField.KERNEL_VERSION:
        return 'Kernel Version';
      case ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES:
        return 'Mac Addresses';
      case ForemanRegexClientRuleForemanStringField.OS_RELEASE:
        return 'OS Release';
      case ForemanRegexClientRuleForemanStringField.OS_VERSION:
        return 'OS Version';
      case ForemanRegexClientRuleForemanStringField.SYSTEM:
        return 'System';
      case ForemanRegexClientRuleForemanStringField.UNSET:
        return 'Unset';
      case ForemanRegexClientRuleForemanStringField.USERNAMES:
        return 'User Names';
      default:
        checkExhaustive(ruleType);
    }
  }
}
