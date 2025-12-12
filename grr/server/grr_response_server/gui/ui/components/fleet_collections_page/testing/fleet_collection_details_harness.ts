import {ComponentHarness} from '@angular/cdk/testing';
import {MatTabLinkHarness} from '@angular/material/tabs/testing';

import {ApprovalChipHarness} from '../../shared/testing/approval_chip_harness';
import {FleetCollectionApprovalsHarness} from '../fleet_collection_approvals/testing/fleet_collection_approvals_harness';
import {FleetCollectionConfigurationHarness} from '../fleet_collection_configuration/testing/fleet_collection_configuration_harness';
import {FleetCollectionDebuggingHarness} from '../fleet_collection_debugging/testing/fleet_collection_debugging_harness';
import {FleetCollectionResultsHarness} from '../fleet_collection_results/testing/fleet_collection_results_harness';

/** Harness for the FleetCollectionDetails component. */
export class FleetCollectionDetailsHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-details';

  readonly tabs = this.locatorForAll(MatTabLinkHarness);
  readonly approvalChip = this.locatorForOptional(ApprovalChipHarness);

  private readonly resultsComponent = this.locatorForOptional(
    FleetCollectionResultsHarness,
  );
  private readonly configurationComponent = this.locatorForOptional(
    FleetCollectionConfigurationHarness,
  );
  private readonly debuggingComponent = this.locatorForOptional(
    FleetCollectionDebuggingHarness,
  );
  private readonly approvalsComponent = this.locatorForOptional(
    FleetCollectionApprovalsHarness,
  );

  async hasResultsComponent(): Promise<boolean> {
    return !!(await this.resultsComponent());
  }

  async hasConfigurationComponent(): Promise<boolean> {
    return !!(await this.configurationComponent());
  }

  async hasDebuggingComponent(): Promise<boolean> {
    return !!(await this.debuggingComponent());
  }

  async hasApprovalsComponent(): Promise<boolean> {
    return !!(await this.approvalsComponent());
  }
}
