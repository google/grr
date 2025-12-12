import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressBarModule} from '@angular/material/progress-bar';
import {MatTooltipModule} from '@angular/material/tooltip';
import {RouterModule} from '@angular/router';

import {
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
  ForemanLabelClientRuleMatchMode,
  ForemanRegexClientRuleForemanStringField,
} from '../../../lib/api/api_interfaces';
import {Hunt} from '../../../lib/models/hunt';
import {checkExhaustive} from '../../../lib/utils';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';
import {HumanReadableDurationPipe} from '../../../pipes/human_readable/human_readable_duration_pipe';
import {CopyButton} from '../copy_button';
import {OutputPluginsForm} from './output_plugins_form';

// Rollout speed
/** Standard rollout speed for fleet collections. */
export const ROLLOUT_SPEED_STANDARD = 200;
/** Unlimited rollout speed for fleet collections. */
export const ROLLOUT_SPEED_UNLIMITED = 0;

// Sample size
/** Small sample size for fleet collections. */
export const SAMPLE_SIZE_SMALL = BigInt(100);
/** Unlimited sample size for fleet collections. */
export const SAMPLE_SIZE_UNLIMITED = BigInt(0);

/** Page displaying this fleet collection arguments. */
@Component({
  selector: 'fleet-collection-arguments',
  templateUrl: './fleet_collection_arguments.ng.html',
  styleUrls: ['./fleet_collection_arguments.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    CopyButton,
    HumanReadableByteSizePipe,
    HumanReadableDurationPipe,
    RouterModule,
    MatDividerModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule,
    OutputPluginsForm,
  ],
})
export class FleetCollectionArguments {
  readonly fleetCollection = input.required<Hunt>();

  protected readonly checkExhaustive = checkExhaustive;

  protected readonly ForemanRegexClientRuleForemanStringField =
    ForemanRegexClientRuleForemanStringField;
  protected readonly ForemanIntegerClientRuleForemanIntegerField =
    ForemanIntegerClientRuleForemanIntegerField;
  protected readonly ForemanClientRuleSetMatchMode =
    ForemanClientRuleSetMatchMode;
  protected readonly ForemanLabelClientRuleMatchMode =
    ForemanLabelClientRuleMatchMode;
  protected readonly ForemanIntegerClientRuleOperator =
    ForemanIntegerClientRuleOperator;
  protected readonly ForemanClientRuleType = ForemanClientRuleType;

  protected readonly SAMPLE_SIZE_SMALL = SAMPLE_SIZE_SMALL;
  protected readonly SAMPLE_SIZE_UNLIMITED = SAMPLE_SIZE_UNLIMITED;
  protected readonly ROLLOUT_SPEED_STANDARD = ROLLOUT_SPEED_STANDARD;
  protected readonly ROLLOUT_SPEED_UNLIMITED = ROLLOUT_SPEED_UNLIMITED;

  protected isNull(value: bigint) {
    return value === BigInt(0);
  }
}
