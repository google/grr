import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';
import * as d3 from 'd3';

import {
  ChartLegend,
  ChartLegendConfiguration,
} from '../../../../lib/dataviz/chart_legend';
import {
  BaseLineChartDataset,
  LineChart,
  LineChartConfiguration,
  LineChartDatapoint,
} from '../../../../lib/dataviz/line_chart';
import {isNonNull, isNull} from '../../../../lib/preconditions';
import {TimestampModule} from '../../../timestamp/module';

const COMPLETED_CLIENTS_CHART_COLOR = '#6DD58C';
const IN_PROGRESS_CLIENTS_CHART_COLOR = '#C4EED0';

/** Provides client completion progress data for a Hunt in chart format. */
@Component({
  selector: 'app-hunt-progress-chart',
  templateUrl: './hunt_progress_chart.ng.html',
  styleUrls: ['./hunt_progress_chart.scss'],
  standalone: true,
  imports: [CommonModule, MatTooltipModule, TimestampModule],
})
export class HuntProgressChart implements AfterViewInit, OnDestroy {
  @Input()
  set chartProgressData(
    chartData: HuntProgressLineChartDataset | null | undefined,
  ) {
    this.chartData = chartData;

    if (!this.templateIsReady || !this.hasDataForChart) return;

    if (isNull(this.huntProgressChart)) {
      this.renderLineChart();
    } else {
      this.huntProgressChart.updateChartDataset(this.chartData!);
    }
  }

  @ViewChild('progressChartContainer')
  private readonly progressChartContainerRef!: ElementRef<HTMLDivElement>;

  private templateIsReady = false;
  private chartData: HuntProgressLineChartDataset | null | undefined;

  huntProgressChart: HuntProgressChartD3 | undefined;

  get hasDataForChart(): boolean {
    if (isNull(this.chartData)) return false;

    // We need at least 2 datapoints in a series in order to render a line:
    return (
      this.chartData.completedClients.length >= 2 ||
      this.chartData.inProgressClients.length >= 2
    );
  }

  constructor(private readonly cdr: ChangeDetectorRef) {}

  ngAfterViewInit() {
    this.templateIsReady = true;

    if (!this.hasDataForChart) return;

    this.renderLineChart();

    /**
     * Angular doesn't like when values used in the template (in this
     * case `*ngIf="!huntProgressChart"`) change inside ngAfterViewInit()
     * lifecycle-hook. If this happens, Angular will throw an
     * ExpressionChangedAfterItHasBeenCheckedError runtime error (only in Dev.
     * mode).
     *
     * In this case, it is OK for us to wait to the template to be ready before
     * rendering the line chart (reason for using ngAfterViewInit). The drawback
     * of this is that the template condition `*ngIf="!huntProgressChart"` will
     * trigger the ExpressionChangedAfterItHasBeenCheckedError runtime error in
     * Dev. mode.
     *
     * As a solution, we manually run change detection after initializing
     * `this.huntProgressChart`. Another possible solution would be to call
     * `this.huntProgressChart = new HuntProgressChartD3(...)` asynchronously
     * inside a setTimeout().
     *
     * For more info:
     * https://hackernoon.com/everything-you-need-to-know-about-the-expressionchangedafterithasbeencheckederror-error-e3fd9ce7dbb4
     */
    this.cdr.detectChanges();
  }

  ngOnDestroy() {
    this.huntProgressChart?.removeEventListeners();
  }

  private renderLineChart(): void {
    this.huntProgressChart = new HuntProgressChartD3(
      this.progressChartContainerRef.nativeElement,
      this.chartData!,
    );
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

  updateChartDataset(chartData: HuntProgressLineChartDataset): void {
    if (isNonNull(this.lineChart)) {
      this.lineChart.updateDataset(chartData);
    }
  }

  removeEventListeners(): void {
    this.lineChart?.removeEventListeners();
  }
}
