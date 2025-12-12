import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
} from '@angular/core';
import * as d3 from 'd3';

import {
  CollectFilesByKnownPathResult,
  CollectFilesByKnownPathResultStatus,
} from '../../../lib/api/api_interfaces';
import {
  translateHashToHex,
  translateStatEntry,
} from '../../../lib/api/translation/flow';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {checkExhaustive} from '../../../lib/utils';
import {
  CollectionState,
  CollectionStatus,
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';

// Margin and size of the bar chart.
const MARGIN = {top: 20, right: 30, bottom: 40, left: 90};
const WIDTH = 400 - MARGIN.left - MARGIN.right;
const HEIGHT = 200 - MARGIN.top - MARGIN.bottom;

const TRANSITION_DURATION = 250;

interface BarChartEntry {
  state: CollectionState;
  stateString: string;
  color: string;
  count: number;
}

function flowFileResultFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly FlowFileResult[] {
  return collectionResults
    .map((flowResult) => {
      const payload = flowResult.payload as CollectFilesByKnownPathResult;
      return {
        statEntry: translateStatEntry(payload.stat!),
        hashes: translateHashToHex(payload.hash ?? {}),
        status: collectionStatusFromCollectFilesByKnownPathResultStatus(
          payload.status,
        ),
        clientId: flowResult.clientId,
      };
    })
    .filter(
      (result) =>
        // Filter for final result states as flow results also include
        // intermediate/inprogress results, so a for a successfully collected
        // file, there will be at least two results, one with status=SUCCESS and
        // one with status=IN_PROGRESS, and we only want to show the final
        // result.
        result.status.state === CollectionState.ERROR ||
        result.status.state === CollectionState.SUCCESS,
    );
}

function collectionStatusFromCollectFilesByKnownPathResultStatus(
  status: CollectFilesByKnownPathResultStatus | undefined,
): CollectionStatus {
  if (!status) {
    return {state: CollectionState.UNKNOWN};
  }
  switch (status) {
    case CollectFilesByKnownPathResultStatus.COLLECTED:
      return {state: CollectionState.SUCCESS};
    case CollectFilesByKnownPathResultStatus.IN_PROGRESS:
      return {state: CollectionState.IN_PROGRESS};
    case CollectFilesByKnownPathResultStatus.NOT_FOUND:
      return {state: CollectionState.ERROR, message: 'File not found'};
    case CollectFilesByKnownPathResultStatus.FAILED:
      return {state: CollectionState.ERROR, message: 'Unknown error'};
    case CollectFilesByKnownPathResultStatus.UNDEFINED:
      return {state: CollectionState.UNKNOWN};
    default:
      checkExhaustive(status);
  }
}

/**
 * Component that displays results of CollectFilesByKnownPath flow.
 */
@Component({
  selector: 'collect-files-by-known-path-results',
  templateUrl: './collect_files_by_known_path_results.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, FileResultsTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectFilesByKnownPathResults implements AfterViewInit {
  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  protected flowFileResults = computed(() => {
    return flowFileResultFromCollectionResults(this.collectionResults());
  });

  protected isHuntResult = computed(() => {
    return this.collectionResults().some(isHuntResult);
  });

  // Bar chart.
  protected svg?: d3.Selection<SVGGElement, {}, HTMLElement, unknown>;
  protected xAxisGroup?: d3.Selection<SVGGElement, {}, HTMLElement, unknown>;
  protected yAxisGroup?: d3.Selection<SVGGElement, {}, HTMLElement, unknown>;
  protected xScale = d3.scaleLinear<number, number>().range([0, WIDTH]);
  protected yScale = d3.scaleBand().range([0, HEIGHT]).padding(0.2);

  protected readonly barChartEntries = computed(() => {
    const errorPaths = this.flowFileResults()
      .filter((res) => res.status?.state === CollectionState.ERROR)
      .map((res) => res.statEntry.pathspec?.path ?? '');
    const successPaths = this.flowFileResults()
      .filter((res) => res.status?.state === CollectionState.SUCCESS)
      .map((res) => res.statEntry.pathspec?.path ?? '');
    const inProgressPaths = new Set<string>(
      this.flowFileResults()
        .filter((res) => res.status?.state === CollectionState.IN_PROGRESS)
        .map((res) => res.statEntry.pathspec?.path ?? '')
        // Filter out paths that are already in the other two sets. Every flow
        // writes it's progress to the flow results database and does not remove
        // the previous results, so every path will have at least one progress
        // result and one final result.
        .filter((path) => !successPaths.includes(path))
        .filter((path) => !errorPaths.includes(path)),
    );

    return [
      {
        state: CollectionState.IN_PROGRESS,
        stateString: 'In Progress',
        color: '#ffb300',
        count: inProgressPaths.size,
      },
      {
        state: CollectionState.SUCCESS,
        stateString: 'Success',
        color: '#43a047',
        count: successPaths.length,
      },
      {
        state: CollectionState.ERROR,
        stateString: 'Error',
        color: '#e53935',
        count: errorPaths.length,
      },
    ];
  });

  constructor() {
    effect(() => {
      this.updateBarChart(this.barChartEntries());
    });
  }

  updateBarChart(collectionStatuses: BarChartEntry[]) {
    if (this.svg && this.xAxisGroup && this.yAxisGroup) {
      // Update scales with new data.
      this.xScale.domain([
        0,
        d3.max(collectionStatuses.map((d) => d.count)) ?? 0,
      ]);
      this.yScale.domain(collectionStatuses.map((d) => d.stateString));

      // Update axes.
      this.xAxisGroup
        .transition()
        .duration(TRANSITION_DURATION)
        // tslint:disable-next-line:no-any
        .call(d3.axisBottom(this.xScale) as any);
      this.yAxisGroup
        .transition()
        .duration(TRANSITION_DURATION)
        // tslint:disable-next-line:no-any
        .call(d3.axisLeft(this.yScale) as any);

      // Update the bars.
      const bars = this.svg.selectAll('rect').data(collectionStatuses);

      bars
        .enter()
        .append('rect')
        .transition()
        .duration(TRANSITION_DURATION)
        .attr('x', (d) => this.xScale!(0))
        .attr('y', (d) => this.yScale!(d.stateString) ?? '')
        .attr('width', (d) => this.xScale!(d.count))
        .attr('height', this.yScale!.bandwidth())
        .attr('fill', (d) => d.color);

      // Exit: Remove bars for removed data.
      bars.exit().remove();
    }
  }

  ngAfterViewInit() {
    // Append the svg to the div.
    this.svg = d3
      .select('#collect_files_by_known_path_stats')
      .append('svg')
      .attr('width', WIDTH + MARGIN.left + MARGIN.right)
      .attr('height', HEIGHT + MARGIN.top + MARGIN.bottom)
      .append('g')
      // tslint:disable-next-line:no-any
      .attr('transform', `translate(${MARGIN.left}, ${MARGIN.top})`) as any;

    // Append axes to the svg.
    this.xAxisGroup = this.svg!.append('g').attr(
      'transform',
      `translate(0, ${HEIGHT})`,
    );
    this.yAxisGroup = this.svg!.append('g');

    // Update scales with initial data.
    this.updateBarChart(this.barChartEntries());
  }
}
