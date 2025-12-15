import {ComponentHarness} from '@angular/cdk/testing';

import {CollapsibleTitleHarness} from '../../../shared/testing/collapsible_container_harness';
import {FleetCollectionProgressChartHarness} from './fleet_collection_progress_chart_harness';
import {FleetCollectionProgressTableHarness} from './fleet_collection_progress_table_harness';

/** Harness for the FleetCollectionProgress component. */
export class FleetCollectionProgressHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-progress';

  private readonly collectionSummaries = this.locatorForAll('.summary');
  readonly collapsibleTitles = this.locatorForAll(CollapsibleTitleHarness);
  readonly progressChart = this.locatorForOptional(
    FleetCollectionProgressChartHarness,
  );

  readonly progressTable = this.locatorForOptional(
    FleetCollectionProgressTableHarness,
  );

  private readonly noProgressData =
    this.locatorForOptional('.no-progress-data');

  async getCollectionSummaries(): Promise<string[]> {
    const summaries = await this.collectionSummaries();
    return Promise.all(summaries.map((summary) => summary.text()));
  }

  async getNoProgressData(): Promise<string | undefined> {
    return (await this.noProgressData())?.text();
  }
}
