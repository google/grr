import {ComponentHarness} from '@angular/cdk/testing';
import {MatTabNavBarHarness} from '@angular/material/tabs/testing';

import {ClientFlowsHarness} from '../client_flows/testing/client_flows_harness';
import {ClientHistoryHarness} from '../client_history/testing/client_history_harness';
import {ClientOverviewHarness} from './client_overview_harness';

/** Harness for the ClientPage component. */
export class ClientPageHarness extends ComponentHarness {
  static hostSelector = 'client-page';

  private readonly clientOverview = this.locatorFor(ClientOverviewHarness);
  private readonly tabBar = this.locatorFor(MatTabNavBarHarness);

  private readonly clientHistory =
    this.locatorForOptional(ClientHistoryHarness);
  private readonly clientFlows = this.locatorForOptional(ClientFlowsHarness);

  async getClientOverviewHarness(): Promise<ClientOverviewHarness> {
    return this.clientOverview();
  }

  async getTabNavBar(): Promise<MatTabNavBarHarness> {
    return this.tabBar();
  }

  async isClientHistoryVisible(): Promise<boolean> {
    return !!(await this.clientHistory());
  }

  async isClientFlowsVisible(): Promise<boolean> {
    return !!(await this.clientFlows());
  }
}
