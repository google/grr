import * as d3 from 'd3';

import {
  DEFAULT_PADDING_PX,
  PaddingConfiguration,
  toCSSPaddingValue,
} from './padding';

declare interface LegendItemConfiguration {
  label: string;
  color: string;
}

/** LegendOrientation Defines the  */
export enum LegendOrientation {
  HORIZONTAL = 'HORIZONTAL',
  VERTICAL = 'VERTICAL',
}

/** Configuration object for the legend to be rendered. */
export declare interface ChartLegendConfiguration {
  orientation?: LegendOrientation;
  padding?: PaddingConfiguration | number;
  items: LegendItemConfiguration[];
}

const DEFAULT_ORIENTATION = LegendOrientation.HORIZONTAL;
const GAP_BETWEEN_ITEMS = '20px';
const GAP_BETWEEN_SQUARE_AND_LABEL = '10px';
const ITEM_SQUARE_SIZE = '20px';

/** Renders a basic Legend to provide more context for charts */
export class ChartLegend {
  private legendContainer?: d3.Selection<
    HTMLDivElement,
    undefined,
    null,
    undefined
  >;
  private readonly legendOrientation: LegendOrientation = DEFAULT_ORIENTATION;
  private readonly legendPaddingPx: PaddingConfiguration = {
    topPx: DEFAULT_PADDING_PX,
    rightPx: DEFAULT_PADDING_PX,
    bottomPx: DEFAULT_PADDING_PX,
    leftPx: DEFAULT_PADDING_PX,
  };

  constructor(
    private readonly container: Element,
    private readonly configuration: ChartLegendConfiguration,
  ) {
    this.legendOrientation =
      this.configuration.orientation ?? DEFAULT_ORIENTATION;

    if (this.configuration.padding != null) {
      if (typeof this.configuration.padding === 'number') {
        this.legendPaddingPx = {
          topPx: this.configuration.padding,
          bottomPx: this.configuration.padding,
          leftPx: this.configuration.padding,
          rightPx: this.configuration.padding,
        };
      } else {
        this.legendPaddingPx = this.configuration.padding;
      }
    }
  }

  renderLegend(): void {
    this.legendContainer = d3
      .select<d3.BaseType, undefined>(this.container)
      .append('div')
      .style('display', 'flex')
      .style('gap', GAP_BETWEEN_ITEMS)
      .attr('class', 'legend-container');

    if (this.legendOrientation === LegendOrientation.HORIZONTAL) {
      // 'row' is the default value for 'flex-direction', but we want to be
      // explicit:
      this.legendContainer.style('flex-direction', 'row');
    }

    if (this.legendOrientation === LegendOrientation.VERTICAL) {
      this.legendContainer.style('flex-direction', 'column');
    }

    this.legendContainer.style(
      'padding',
      toCSSPaddingValue(this.legendPaddingPx),
    );

    this.configuration.items.forEach((item) => {
      const itemContainer = this.legendContainer!.append('div')
        .attr('class', 'legend-item')
        .style('display', 'flex')
        .style('align-items', 'center')
        .style('gap', GAP_BETWEEN_SQUARE_AND_LABEL);

      // We append the coloured square
      itemContainer
        .append('div')
        .attr('class', 'legend-item-square')
        .style('width', ITEM_SQUARE_SIZE)
        .style('height', ITEM_SQUARE_SIZE)
        .style('background-color', item.color);

      // We append the label
      itemContainer
        .append('div')
        .attr('class', 'legend-item-label')
        .text(item.label);
    });
  }
}
