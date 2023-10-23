import {ChartLegend, ChartLegendConfiguration, LegendOrientation} from './chart_legend';

describe('ChartLegend', () => {
  let testParentContainer: HTMLDivElement;
  let chartLegend: ChartLegend;

  beforeEach(() => {
    testParentContainer = document.createElement('div');
    document.body.appendChild(testParentContainer);
  });

  it('renders one legend item', () => {
    const config: ChartLegendConfiguration = {
      items: [
        {
          label: 'Test',
          color: 'red',
        },
      ],
    };

    chartLegend = new ChartLegend(testParentContainer, config);

    chartLegend.renderLegend();

    const legendContainer =
        testParentContainer.querySelector('.legend-container');
    expect(legendContainer).not.toBeNull();

    const legendItems = legendContainer!.querySelectorAll('.legend-item');
    expect(legendItems.length).toBe(1);

    const legendItemLabel = legendItems[0].querySelector('.legend-item-label');
    const legendItemSquare =
        legendItems[0].querySelector<HTMLDivElement>('.legend-item-square');

    expect(legendItemLabel!.textContent).toContain('Test');
    expect(legendItemSquare!.style.backgroundColor).toEqual('red');
  });

  it('renders multiple legend items', () => {
    const config: ChartLegendConfiguration = {
      items: [
        {
          label: 'Test',
          color: 'red',
        },
        {
          label: 'Patata',
          color: 'blue',
        },
        {
          label: 'Lorem Ipsum',
          color: 'green',
        },
      ],
    };

    chartLegend = new ChartLegend(testParentContainer, config);

    chartLegend.renderLegend();

    const legendContainer =
        testParentContainer.querySelector('.legend-container');
    expect(legendContainer).not.toBeNull();

    const legendItems = legendContainer!.querySelectorAll('.legend-item');
    expect(legendItems.length).toBe(3);

    const legendItemLabels =
        legendContainer!.querySelectorAll('.legend-item-label');
    const legendItemSquares = legendContainer!.querySelectorAll<HTMLDivElement>(
        '.legend-item-square');

    expect(legendItemLabels[0].textContent).toContain('Test');
    expect(legendItemSquares[0].style.backgroundColor).toEqual('red');

    expect(legendItemLabels[1].textContent).toContain('Patata');
    expect(legendItemSquares[1].style.backgroundColor).toEqual('blue');

    expect(legendItemLabels[2].textContent).toContain('Lorem Ipsum');
    expect(legendItemSquares[2].style.backgroundColor).toEqual('green');
  });

  it('Does not render any legend items', () => {
    const config: ChartLegendConfiguration = {
      items: [],
    };

    chartLegend = new ChartLegend(testParentContainer, config);

    chartLegend.renderLegend();

    const legendContainer =
        testParentContainer.querySelector('.legend-container');
    expect(legendContainer).not.toBeNull();

    const legendItems = legendContainer!.querySelectorAll('.legend-item');
    expect(legendItems.length).toBe(0);
  });

  it('renders legend items vertically', () => {
    const config: ChartLegendConfiguration = {
      orientation: LegendOrientation.VERTICAL,
      items: [],
    };

    chartLegend = new ChartLegend(testParentContainer, config);

    chartLegend.renderLegend();

    const legendContainer =
        testParentContainer.querySelector<HTMLDivElement>('.legend-container');
    expect(legendContainer).not.toBeNull();
    expect(legendContainer!.style.flexDirection).toEqual('column');
  });

  it('renders legend items horizontally', () => {
    const config: ChartLegendConfiguration = {
      items: [],
      orientation: LegendOrientation.HORIZONTAL,
    };

    chartLegend = new ChartLegend(testParentContainer, config);

    chartLegend.renderLegend();

    const legendContainer =
        testParentContainer.querySelector<HTMLDivElement>('.legend-container');
    expect(legendContainer).not.toBeNull();
    expect(legendContainer!.style.flexDirection).toEqual('row');
  });
});
