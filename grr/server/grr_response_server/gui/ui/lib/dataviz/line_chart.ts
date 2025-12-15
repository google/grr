import * as d3 from 'd3';

import {DEFAULT_PADDING_PX, PaddingConfiguration} from './padding';

/** Data Structure defining a single data-point in the Line Chart */
export declare interface LineChartDatapoint {
  y: number;
  x: number;
}

/**
 * Data structure definition that contains the different series to render in the
 * chart.
 *
 * Example:
 *   interface NumbersLineChartDataset extends
 *       BaseLineChartDataset {
 *     one: LineChartDatapoint[];
 *     two: LineChartDatapoint[];
 *   }
 */
export declare type BaseLineChartDataset = Record<string, LineChartDatapoint[]>;

declare interface LineChartSizing {
  /** If not specified, the chart will take its parent's width */
  widthPx?: number;
  /** By default the height will be half of the width: */
  heightToWidthRatio?: number;
  /**
   * Spacing between the chart container element and the chart ploting space.
   * This is useful to prevent Axis labels from being cropped involuntarily.
   */
  padding?: PaddingConfiguration | number;
  /**
   * If true, the chart will listen to size changes on the parent HTML node
   * and will resize itself to fit the entire width and always respecting the
   * heightToWidth ratio.
   */
  rerenderOnResize?: boolean;
}

/** Configuration options for the Line Chart */
export declare interface LineChartConfiguration<
  LineChartDataset extends BaseLineChartDataset,
> {
  scale?: {
    x?: d3.ScaleLinear<number, number>;
    y?: d3.ScaleLinear<number, number>;
  };
  sizing?: LineChartSizing;
  /**
   * Each line/area can be configurted through this property. `SeriesKey` stands
   * for the key used in the dataset dictionary object. For example in the
   * following dataset, `SeriesKey` would effectively be 'lineOne' | 'lineTwo':
   *
   * const dataset = {
   *   lineOne: [{ x:1, y:3}, {x:2, y: 4}],
   *   lineTwo: [{ x:1, y:1}, {x:2, y: 3}],
   * };
   *
   * This allows us to know which line the configuration should apply to.
   */
  series?: {
    [SeriesKey in keyof LineChartDataset]?: LineChartSeriesConfiguration;
  };
}

/** Configuration object for each line/area in the chart. */
declare interface LineChartSeriesConfiguration {
  /** If not specified, "SeriesKey" will be used as the id. */
  id?: string;
  /** Colors the area between the line and X-Axis. */
  color?: string;
  /** If true it will render an area, otherwise only a line. */
  isArea?: boolean;
  /**
   * Determines the order (z-axis position relative to the user) of the line.
   * The higher the order, the more in front the line/area will be.
   * E.g. `1` is drawn first (so will be in the back), and
   *      `2` is drawn second (in front/on top of 1)
   */
  order?: number;
}

/** Defines the default transition time for line-chart animations */
export const DEFAULT_TRANSITION_TIME_MS = 500;
// body-1 Angular Material typography level:
const DEFAULT_AXIS_LABEL_FRONT_SIZE = '14px';
/** Defines the default height-to-width relationship of the chart */
export const DEFAULT_HEIGHT_TO_WIDTH_RATIO = 1 / 2;
const AXIS_COLOR = '#757575'; // Mat. $grey-palette 600
const AXIS_TICKS_PER_WIDTHPX_RATIO = 1 / 80;

// https://github.com/d3/d3-time-format
const X_AXIS_LABEL_DATE_FORMAT = '%H:%M:%S';
const X_AXIS_SUBLABEL_DATE_FORMAT = '%b %d';
const X_AXIS_SUBLABEL_DATE_FORMAT_WITH_YEAR = '%b %d %Y';
const X_AXIS_SUBLABEL_MARGIN_PX = 20;
const CURRENT_YEAR = new Date().getFullYear();

/**
 * Note: We want to provide information about the date(s) of the Hunt in the
 * chart without being redundant in every X Axis tick label. For this reason,
 * the decided approach is to show the time (hh:mm:ss) in every tick label,
 * and show the date in a subtitle label. Each date will only be added once,
 * meaning that if a Hunt happens entirely in the same calendar day, that day
 * will only be shown once below the first tick starting from the left. If a
 * hunt spans multiple days, then multiple date subtitle labels will be
 * shown, without being repeated.
 */
const toXAxisDateLabel = d3.timeFormat(X_AXIS_LABEL_DATE_FORMAT);
const toXAxisDateSubLabel = d3.timeFormat(X_AXIS_SUBLABEL_DATE_FORMAT);
const toXAxisDateSubLabelWithYear = d3.timeFormat(
  X_AXIS_SUBLABEL_DATE_FORMAT_WITH_YEAR,
);

const HEX_CHAR_RANGE = '0123456789ABCDEF';
function generateRandomHexColor(): string {
  let color = '#';

  for (let i = 0; i < 6; i++) {
    color += HEX_CHAR_RANGE[Math.floor(Math.random() * 16)];
  }

  return color;
}

/**
 * LineChart renders a line-chart in the given parent HTML node element, with
 * the given configuration.
 */
export class LineChart<LineChartDataset extends BaseLineChartDataset> {
  private readonly parentNodeSelection: d3.Selection<
    d3.BaseType,
    undefined,
    d3.BaseType,
    undefined
  >;
  private chartSvgContainer?: d3.Selection<
    SVGSVGElement,
    undefined,
    d3.BaseType,
    undefined
  >;

  private readonly transitionDurationMs = DEFAULT_TRANSITION_TIME_MS;

  private containerWidthPx = 0;
  private chartHeightPx = 0;
  private chartWidthPx = 0;
  private chartPaddingPx: PaddingConfiguration = {
    topPx: DEFAULT_PADDING_PX,
    rightPx: DEFAULT_PADDING_PX,
    bottomPx: DEFAULT_PADDING_PX,
    leftPx: DEFAULT_PADDING_PX,
  };

  private xScale?: d3.ScaleLinear<number, number>;
  private yScale?: d3.ScaleLinear<number, number>;
  private xAxis?: d3.Axis<number>;
  private yAxis?: d3.Axis<number>;

  private resizeObserver?: ResizeObserver;

  get xAxisTopMarginPx(): number {
    return this.chartHeightPx - this.chartPaddingPx.bottomPx;
  }

  get yAxisLeftMarginPx(): number {
    return this.chartPaddingPx.leftPx;
  }

  /**
   * If the viewport is small, we want less ticks as there might be overlap
   * between the labels. For this reason we make the tick number dynamic for
   * the X and Y Axis.
   */
  get xAxisTicks(): number {
    return this.chartPlotWidthPx * AXIS_TICKS_PER_WIDTHPX_RATIO;
  }

  get yAxisTicks(): number {
    const heightToWidthRatio =
      this.configuration?.sizing?.heightToWidthRatio ??
      DEFAULT_HEIGHT_TO_WIDTH_RATIO;

    const yAxisTicksPerHeightPxRatio =
      AXIS_TICKS_PER_WIDTHPX_RATIO / heightToWidthRatio;

    return this.chartPlotHeightPx * yAxisTicksPerHeightPxRatio;
  }

  get chartPlotWidthPx(): number {
    return (
      this.chartWidthPx -
      this.chartPaddingPx.leftPx -
      this.chartPaddingPx.rightPx
    );
  }

  get chartPlotHeightPx(): number {
    return (
      this.chartHeightPx -
      this.chartPaddingPx.topPx -
      this.chartPaddingPx.bottomPx
    );
  }

  constructor(
    private readonly parentNode: Element,
    private dataset: LineChartDataset,
    private readonly configuration?: LineChartConfiguration<LineChartDataset>,
  ) {
    this.setChartSize(parentNode, configuration?.sizing);
    this.setChartPadding(configuration?.sizing?.padding);

    this.parentNodeSelection = d3.select<d3.BaseType, undefined>(
      this.parentNode,
    );

    this.initializeScales();
    this.setAxisScales();
    this.setAxisTicks();
  }

  updateDataset(dataset: LineChartDataset): void {
    this.dataset = dataset;

    this.recalculateScaleDomains(this.dataset);
    this.updateBothAxis();

    this.redrawLines();
  }

  // There is currently no way of detecting the destruction of a "pure" Class
  // In JavaScript/TypeScript. Therefore we need to expose the following method:
  removeEventListeners(): void {
    if (this.resizeObserver != null) {
      this.resizeObserver.disconnect();
    }
  }

  initialChartRender(): void {
    this.renderChartElements();

    this.setupEventListeners();
  }

  private renderChartElements(): void {
    this.chartSvgContainer = this.parentNodeSelection
      .append('svg')
      .attr('class', 'chart-container')
      .attr('width', `${this.chartWidthPx}px`)
      .attr('height', `${this.chartHeightPx}px`);

    this.recalculateScaleDomains(this.dataset);
    this.renderPaths();
    this.renderBothAxis();
  }

  private renderPaths(): void {
    const datasetKeys = this.getCurrentDatasetKeys();

    const pathContainer = this.chartSvgContainer!.append('g').attr(
      'class',
      'path-container',
    );

    // The rendering order of the "path" elements is relevant, as the latest
    // sibling will always be shown in front of the previous sibling.
    // For this reason, we render paths on a low-to-high order value:
    const datasetKeysSortedByOrder = datasetKeys.sort((aKey, bKey) => {
      return this.getLineOrder(aKey) - this.getLineOrder(bKey);
    });

    datasetKeysSortedByOrder.forEach((key) => {
      const color = this.getLineColor(key);
      const lineId = this.getLineId(key);

      const path = pathContainer
        .append('path')
        .datum(this.dataset[key])
        .attr('class', `series-path`)
        .attr('id', lineId)
        .style('stroke', color);

      if (this.getLineIsArea(key)) {
        // We want an area:
        path.attr('d', this.getAreaGenerator()).style('fill', color);
      } else {
        // We only want a line:
        path.attr('d', this.getLineGenerator()).style('fill', 'none');
      }
    });
  }

  private recalculateScaleDomains(dataset: LineChartDataset): void {
    const allChartDatapoints = this.getDatasetDatapoints(dataset);

    const allXValues = allChartDatapoints.map((dp) => dp.x);
    const allYValues = allChartDatapoints.map((dp) => dp.y);

    this.xScale!.domain([d3.min(allXValues)!, d3.max(allXValues)!]);
    this.yScale!.domain([d3.min(allYValues)!, d3.max(allYValues)!]);
  }

  private renderBothAxis(): void {
    const axisContainer = this.chartSvgContainer!.append('g')
      .attr('class', 'axis-container')
      .style('color', AXIS_COLOR);

    axisContainer
      .append('g')
      .attr('class', 'axis x-axis')
      .style('font-size', DEFAULT_AXIS_LABEL_FRONT_SIZE)
      .attr('transform', `translate(0, ${this.xAxisTopMarginPx})`)
      .call(this.xAxis!)
      .call(() => {
        this.updateXAxisTickSubLabels();
      });

    axisContainer
      .append('g')
      .attr('class', 'axis y-axis')
      .style('font-size', DEFAULT_AXIS_LABEL_FRONT_SIZE)
      .attr('transform', `translate(${this.yAxisLeftMarginPx}, 0)`)
      .call(this.yAxis!);
  }

  private updateBothAxis(): void {
    this.xAxis!.ticks(this.xAxisTicks);
    this.yAxis!.ticks(this.yAxisTicks);

    this.selectAxis('x')
      .transition(d3.transition().duration(this.transitionDurationMs))
      .attr('transform', `translate(0, ${this.xAxisTopMarginPx})`)
      .call(this.xAxis!)
      .on('end', () => {
        // Note: We need to asynchronously trigger the function to add the
        // dates to the X Axis labels, as old ticks are still present for some
        // reason. Old ticks being present will cause the wrong dates
        // being added (or no dates at all):
        setTimeout(() => {
          this.updateXAxisTickSubLabels();
        });
      });

    this.selectAxis('y')
      .transition(d3.transition().duration(this.transitionDurationMs))
      .call(this.yAxis!);
  }

  /**
   * Returns an Array containing all the Datapoints of the different series of
   * the dataset, mainly for domain calculation purposes.
   */
  private getDatasetDatapoints(
    dataset: LineChartDataset,
  ): LineChartDatapoint[] {
    const datasetKeys = d3.keys(dataset) as Array<keyof LineChartDataset>;

    return datasetKeys.map((key) => dataset[key]).flat();
  }

  private initializeScales(): void {
    this.xScale = this.configuration?.scale?.x ?? d3.scaleLinear();
    this.yScale = this.configuration?.scale?.y ?? d3.scaleLinear();

    this.resetScalesRange();
  }

  /**
   * We set the coordinate system for the Scale. This allows us to map
   * line-series datapoints to plot-coordinates.
   */
  private resetScalesRange(): void {
    this.xScale!.range([
      this.chartPaddingPx.leftPx,
      this.chartWidthPx - this.chartPaddingPx.rightPx,
    ]);
    this.yScale!.range([
      this.chartHeightPx - this.chartPaddingPx.bottomPx,
      this.chartPaddingPx.topPx,
    ]);
  }

  private setAxisScales(): void {
    this.xAxis = d3.axisBottom(this.xScale!) as d3.Axis<number>;
    this.yAxis = d3.axisLeft(this.yScale!) as d3.Axis<number>;
  }

  private setAxisTicks(): void {
    this.xAxis!.ticks(this.xAxisTicks)
      .tickSizeInner(-this.chartPlotHeightPx)
      .tickFormat((timestamp) => toXAxisDateLabel(new Date(timestamp)));

    this.yAxis!.ticks(this.yAxisTicks);
  }

  /**
   * We add dates to X-Axis tick time labels. Each date will only be added once,
   * meaning that if a Hunt happens entirely in the same calendar day, that day
   * will only be shown once below the first tick starting from the left. If a
   * hunt spans multiple days, then multiple date subtitle labels will be
   * shown, without being repeated.
   */
  private updateXAxisTickSubLabels(): void {
    const alreadyAddedDates = new Set<string>();

    this.selectAxis('x')
      .selectAll<SVGGElement, number>('.tick')
      .each((tickTimestamp, i, nodes) => {
        const tickSubtitleLabelFn =
          new Date(tickTimestamp).getFullYear() < CURRENT_YEAR
            ? toXAxisDateSubLabelWithYear
            : toXAxisDateSubLabel;

        const tickSubtitleText = tickSubtitleLabelFn(new Date(tickTimestamp));

        if (alreadyAddedDates.has(tickSubtitleText)) return;

        alreadyAddedDates.add(tickSubtitleText);

        const currentTick = d3.select(nodes[i]);
        const currentTickLabel = currentTick.select('text');
        const currentTickSubLabel = currentTick.select('.tick-subtitle');

        if (currentTickSubLabel.empty()) {
          const tickSubLabelYPosition =
            +currentTickLabel.attr('y') + X_AXIS_SUBLABEL_MARGIN_PX;

          currentTick
            .append('text')
            .attr('class', 'tick-subtitle')
            .text(tickSubtitleText)
            .style('fill', 'currentColor')
            .attr('y', tickSubLabelYPosition)
            .attr('dy', currentTickLabel.attr('dy'));
        } else {
          currentTickSubLabel.text(tickSubtitleText);
        }
      });
  }

  private getCurrentDatasetKeys(): Array<keyof LineChartDataset> {
    return d3.keys(this.dataset) as Array<keyof LineChartDataset>;
  }

  private getLineGenerator(): d3.Line<LineChartDatapoint> {
    return (
      d3
        .line<LineChartDatapoint>()
        // We filter out incomplete datapoints:
        .defined((dp) => dp.x != null && dp.y != null)
        .x((dp) => this.xScale!(dp.x))
        .y((dp) => this.yScale!(dp.y))
    );
  }

  private getAreaGenerator(): d3.Area<LineChartDatapoint> {
    const lowestYAxisValue = this.yScale!.domain()[0];
    const areaBottomBoundary = this.yScale!(lowestYAxisValue);

    return (
      d3
        .area<LineChartDatapoint>()
        // We filter out incomplete datapoints:
        .defined((dp) => dp.x != null && dp.y != null)
        .x((dp) => this.xScale!(dp.x))
        .y0(areaBottomBoundary)
        .y1((dp) => this.yScale!(dp.y))
    );
  }

  private selectLinePath(key: keyof LineChartDataset) {
    return d3.select<SVGPathElement, LineChartDataset[keyof LineChartDataset]>(
      `.series-path#${this.getLineId(key)}`,
    );
  }

  private selectAxis(axis: 'x' | 'y') {
    return d3.select<SVGGElement, number[]>(`.${axis}-axis`);
  }

  private getElementWidthPx(element: Element): number {
    return element.getBoundingClientRect().width;
  }

  private setChartSize(
    containerElement: Element,
    config?: LineChartSizing,
  ): void {
    if (config?.widthPx != null) {
      this.chartWidthPx = config!.widthPx;
    } else {
      // If we don't specify a width explicitly, it will take the available one,
      // that is, the width of its parent node:
      this.containerWidthPx = this.getElementWidthPx(containerElement);
      this.chartWidthPx = this.containerWidthPx;
    }

    const heightWidthRatio =
      config?.heightToWidthRatio ?? DEFAULT_HEIGHT_TO_WIDTH_RATIO;

    this.chartHeightPx = this.chartWidthPx * heightWidthRatio;
  }

  private setChartPadding(padding?: PaddingConfiguration | number): void {
    if (padding === undefined) return;

    if (typeof padding === 'number') {
      this.chartPaddingPx = {
        topPx: padding,
        bottomPx: padding,
        leftPx: padding,
        rightPx: padding,
      };
    } else {
      this.chartPaddingPx = padding;
    }
  }

  private setupEventListeners(): void {
    if (this.configuration?.sizing?.rerenderOnResize) {
      this.resizeObserver = new ResizeObserver(() => {
        const currentSizeConfig = this.configuration?.sizing || {};
        const containerWidth = this.getElementWidthPx(this.parentNode);

        // If the width of the container element didn't change, we do nothing:
        if (containerWidth === this.containerWidthPx) return;

        this.containerWidthPx = containerWidth;

        const newChartSizeConfiguration: LineChartSizing = {
          ...currentSizeConfig,
          widthPx: this.containerWidthPx,
        };

        requestAnimationFrame(() => {
          this.setChartSize(this.parentNode, newChartSizeConfiguration);
          this.resetScalesRange();
          this.setAxisScales();
          this.setAxisTicks();
          this.redrawChart();
        });
      });

      // We listen to size changes of the chart's container element:
      this.resizeObserver.observe(this.parentNode);
    }
  }

  /**
   * This method assumes there already is a line chart rendered. It will
   * redraw and transition the different elements of the chart (Axis's &
   * lines/areas) based on the current dataset.
   */
  private redrawChart(): void {
    this.chartSvgContainer!.attr('width', `${this.chartWidthPx}px`).attr(
      'height',
      `${this.chartHeightPx}px`,
    );

    this.recalculateScaleDomains(this.dataset);
    this.updateBothAxis();
    this.redrawLines();
  }

  private redrawLines(): void {
    this.getCurrentDatasetKeys().forEach((key) => {
      this.selectLinePath(key)
        // We set the new data for the line:
        .datum(this.dataset[key])
        .transition(d3.transition().duration(this.transitionDurationMs))
        .attr(
          'd',
          this.getLineIsArea(key)
            ? this.getAreaGenerator()
            : this.getLineGenerator(),
        );
    });
  }

  private getLineId(key: keyof LineChartDataset): string {
    const lineConfiguration = this.configuration?.series?.[key];

    return lineConfiguration?.id ?? String(key);
  }

  private getLineOrder(key: keyof LineChartDataset): number {
    const lineConfiguration = this.configuration?.series?.[key];

    return lineConfiguration?.order ?? 0;
  }

  private getLineIsArea(key: keyof LineChartDataset): boolean {
    const lineConfiguration = this.configuration?.series?.[key];

    return lineConfiguration?.isArea ?? false;
  }

  private getLineColor(key: keyof LineChartDataset): string {
    const lineConfiguration = this.configuration?.series?.[key];

    return lineConfiguration?.color ?? generateRandomHexColor();
  }
}
