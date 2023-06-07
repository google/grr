import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyCardModule} from '@angular/material/legacy-card';
import {MatLegacyTooltipModule} from '@angular/material/legacy-tooltip';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {RouterModule} from '@angular/router';

import {ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../lib/api/api_interfaces';
import {Hunt} from '../../../lib/models/hunt';
import {HuntOverviewPageLocalStore} from '../../../store/hunt_overview_page_local_store';
import {toDurationString} from '../../form/duration_input/duration_conversion';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {InfiniteListModule} from '../../helpers/infinite_list/infinite_list_module';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';


/** Page displaying this hunt arguments. */
@Component({
  selector: 'hunt-arguments',
  templateUrl: './hunt_arguments.ng.html',
  styleUrls: ['./hunt_arguments.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntOverviewPageLocalStore],
  imports: [
    CommonModule,
    CopyButtonModule,
    HumanReadableSizeModule,
    RouterModule,
    MatLegacyCardModule,
    MatIconModule,
    MatProgressBarModule,
    MatLegacyTooltipModule,
    InfiniteListModule,
    TimestampModule,
    UserImageModule,
  ],
  standalone: true,
})
export class HuntArguments {
  @Input() hunt: Hunt|null = null;

  protected readonly BigInt = BigInt;
  protected readonly RegexClientRuleForemanStringField =
      ForemanRegexClientRuleForemanStringField;
  protected readonly ClientRuleSetMatchMode = ForemanClientRuleSetMatchMode;
  protected readonly LabelClientRuleMatchMode = ForemanLabelClientRuleMatchMode;
  protected readonly IntegerClientRuleOperator =
      ForemanIntegerClientRuleOperator;
  protected readonly ClientRuleType = ForemanClientRuleType;

  protected readonly regexConditionsNames = new Map<
      ForemanRegexClientRuleForemanStringField|undefined, string>([
    [ForemanRegexClientRuleForemanStringField.UNSET, 'Unset'],
    [ForemanRegexClientRuleForemanStringField.USERNAMES, 'Usernames'],
    [ForemanRegexClientRuleForemanStringField.UNAME, 'Uname'],
    [ForemanRegexClientRuleForemanStringField.FQDN, 'FQDN'],
    [ForemanRegexClientRuleForemanStringField.HOST_IPS, 'Host IPs'],
    [ForemanRegexClientRuleForemanStringField.CLIENT_NAME, 'Client Name'],
    [
      ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
      'Client Description'
    ],
    [ForemanRegexClientRuleForemanStringField.SYSTEM, 'System'],
    [ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES, 'MAC Addresses'],
    [ForemanRegexClientRuleForemanStringField.KERNEL_VERSION, 'Kernel Version'],
    [ForemanRegexClientRuleForemanStringField.OS_VERSION, 'OS Version'],
    [ForemanRegexClientRuleForemanStringField.OS_RELEASE, 'OS Release'],
    [ForemanRegexClientRuleForemanStringField.CLIENT_LABELS, 'Client Labels'],
    [undefined, 'Undefined Condition Field'],
  ]);

  protected readonly integerConditionsNames = new Map<
      ForemanIntegerClientRuleForemanIntegerField|undefined, string>([
    [ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME, 'Install Time'],
    [
      ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
      'Client Version'
    ],
    [
      ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME,
      'Last Boot Time'
    ],
    [ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK, 'Client Clock'],
    [ForemanIntegerClientRuleForemanIntegerField.UNSET, 'Unset'],
    [undefined, 'Undefined Condition Field'],
  ]);

  protected clientRateBucket(clientRate: number) {
    if (clientRate === 0) {
      return 'unlimited';
    } else if (clientRate === 200) {
      return 'standard';
    } else {
      return 'custom';
    }
  }

  protected convertToUnitTime(seconds: BigInt) {
    return toDurationString(Number(seconds), 'long');
  }
}