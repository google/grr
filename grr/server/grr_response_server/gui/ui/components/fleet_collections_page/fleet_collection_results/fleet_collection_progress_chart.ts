import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  Injector,
  input,
  OnDestroy,
  runInInjectionContext,
  ViewChild,
} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';
import * as d3 from 'd3';

import {ApiGetHuntClientCompletionStatsResult} from '../../../lib/api/api_interfaces';
import {
  ChartLegend,
  ChartLegendConfiguration,
} from '../../../lib/dataviz/chart_legend';
import {
  BaseLineChartDataset,
  LineChart,
  LineChartConfiguration,
  LineChartDatapoint,
} from '../../../lib/dataviz/line_chart';

const COMPLETED_CLIENTS_CHART_COLOR = '#6DD58C';
const IN_PROGRESS_CLIENTS_CHART_COLOR = '#C4EED0';

function toChartData(
  progress: ApiGetHuntClientCompletionStatsResult | null | undefined,
): HuntProgressLineChartDataset {
  if (!progress) {
    return {
      completedClients: [],
      inProgressClients: [],
    };
  }

  return {
    completedClients:
      progress.completePoints?.map((point) => ({
        x: (point.xValue ?? 0) * 1000,
        y: point.yValue ?? 0,
      })) ?? [],
    inProgressClients:
      progress.startPoints?.map((point) => ({
        x: (point.xValue ?? 0) * 1000,
        y: point.yValue ?? 0,
      })) ?? [],
  };
}

/** Provides client completion progress data for a Hunt in chart format. */
@Component({
  selector: 'fleet-collection-progress-chart',
  templateUrl: './fleet_collection_progress_chart.ng.html',
  styleUrls: ['./fleet_collection_progress_chart.scss'],
  imports: [CommonModule, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionProgressChart implements AfterViewInit, OnDestroy {
  private readonly injector = inject(Injector);

  @ViewChild('progressChartContainer')
  private readonly progressChartContainerRef!: ElementRef<HTMLDivElement>;

  private huntProgressChart: HuntProgressChartD3 | undefined;

  readonly collectionProgressData = input.required<
    HuntProgressLineChartDataset | null,
    ApiGetHuntClientCompletionStatsResult | null | undefined
  >({transform: toChartData});

  protected readonly hasData = computed(() => {
    if (!this.collectionProgressData) return false;

    // We need at least 2 datapoints in a series in order to render a line:
    const completedClients = this.collectionProgressData()?.completedClients;
    const inProgressClients = this.collectionProgressData()?.inProgressClients;
    if (!completedClients || !inProgressClients) return false;

    return completedClients.length >= 2 || inProgressClients.length >= 2;
  });

  ngAfterViewInit() {
    runInInjectionContext(this.injector, () => {
      effect(() => {
        const collectionProgressData = this.collectionProgressData();
        if (!collectionProgressData) return;

        if (!this.huntProgressChart) {
          this.huntProgressChart = new HuntProgressChartD3(
            this.progressChartContainerRef.nativeElement,
            collectionProgressData,
          );
        } else {
          this.huntProgressChart.updateChartDataset(collectionProgressData);
        }
      });
    });
  }

  ngOnDestroy() {
    this.huntProgressChart?.removeEventListeners();
  }
}

/** Data-structure to be consumed by the Hunt Progress Line Chart */
export declare interface HuntProgressLineChartDataset
  extends BaseLineChartDataset {
  completedClients: LineChartDatapoint[];
  inProgressClients: LineChartDatapoint[];
}

class HuntProgressChartD3 {
  private readonly lineChart:
    | LineChart<HuntProgressLineChartDataset>
    | undefined;
  private readonly chartLegend: ChartLegend;
  private readonly xScale: d3.ScaleLinear<number, number>;

  constructor(
    private readonly container: d3.BaseType,
    private readonly lineChartDataset: HuntProgressLineChartDataset,
  ) {
    const chartContainerSelection = d3.select(this.container);

    const containerNode = chartContainerSelection.append('div').node()!;

    const chartLegendConfig: ChartLegendConfiguration = {
      padding: {
        topPx: 30,
        rightPx: 20,
        bottomPx: 20,
        leftPx: 60,
      },
      items: [
        {
          label: 'Completed',
          color: COMPLETED_CLIENTS_CHART_COLOR,
        },
        {
          label: 'In progress',
          color: IN_PROGRESS_CLIENTS_CHART_COLOR,
        },
      ],
    };

    this.chartLegend = new ChartLegend(containerNode, chartLegendConfig);
    this.chartLegend.renderLegend();

    // We want to share the xScale between charts, so it will live here and be
    // consumed by the future bar-chart:
    this.xScale = d3.scaleLinear();

    const lineChartConfig: LineChartConfiguration<HuntProgressLineChartDataset> =
      {
        scale: {x: this.xScale},
        sizing: {
          padding: {
            topPx: 20,
            rightPx: 50,
            bottomPx: 50,
            leftPx: 60,
          },
          rerenderOnResize: true,
        },
        series: {
          completedClients: {
            color: COMPLETED_CLIENTS_CHART_COLOR,
            isArea: true,
            order: 2,
          },
          inProgressClients: {
            color: IN_PROGRESS_CLIENTS_CHART_COLOR,
            isArea: true,
            order: 1,
          },
        },
      };

    this.lineChart = new LineChart(
      containerNode,
      this.lineChartDataset,
      lineChartConfig,
    );

    this.lineChart.initialChartRender();
  }

  updateChartDataset(
    collectionProgressData: HuntProgressLineChartDataset,
  ): void {
    if (this.lineChart) {
      this.lineChart.updateDataset(collectionProgressData);
    }
  }

  removeEventListeners(): void {
    this.lineChart?.removeEventListeners();
  }
}
