import {
  BaseLineChartDataset,
  DEFAULT_HEIGHT_TO_WIDTH_RATIO,
  DEFAULT_TRANSITION_TIME_MS,
  LineChart,
  LineChartDatapoint,
} from './line_chart';

interface TestLineChartDataset extends BaseLineChartDataset {
  lineOne: LineChartDatapoint[];
}

const emptyTestData: TestLineChartDataset = {
  lineOne: [],
};

const mockLine: LineChartDatapoint[] = [
  {
    x: 10,
    y: 20,
  },
  {
    x: 20,
    y: 10,
  },
];

describe('LineChart', () => {
  let testParentContainer: HTMLDivElement;
  let testChart: LineChart<TestLineChartDataset>;

  beforeEach(() => {
    testParentContainer = document.createElement('div');
    document.body.appendChild(testParentContainer);
  });

  afterEach(() => {
    testParentContainer.remove();
  });

  describe('chart dimensions', () => {
    it('renders a container SVG element with a width and height of 500px', () => {
      testChart = new LineChart(testParentContainer, emptyTestData, {
        sizing: {
          widthPx: 500,
          heightToWidthRatio: 1,
        },
      });

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      expect(chartContainerElement!.getAttribute('width')).toEqual(`500px`);

      expect(chartContainerElement!.getAttribute('height')).toEqual(
        `500px`, // 500 * 1
      );
    });

    it('renders a container SVG element with a width of 500px and height of 250px', () => {
      testChart = new LineChart(testParentContainer, emptyTestData, {
        sizing: {
          widthPx: 500,
          heightToWidthRatio: 0.5,
        },
      });

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      expect(chartContainerElement!.getAttribute('width')).toEqual(`500px`);

      expect(chartContainerElement!.getAttribute('height')).toEqual(
        `250px`, // 500 * 0.5
      );
    });

    it('renders a container SVG element the same width as its container', () => {
      const testWidth = 400;

      testParentContainer.style.width = `${testWidth}px`;

      testChart = new LineChart(testParentContainer, emptyTestData, {
        sizing: {
          widthPx: undefined,
        },
      });

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      expect(chartContainerElement!.getAttribute('width')).toEqual(
        `${testWidth}px`,
      );
    });

    describe('padding', () => {
      it('renders an svg without paddings and a plot area of the same width', () => {
        const testWidth = 400;

        testParentContainer.style.width = `${testWidth}px`;

        testChart = new LineChart(
          testParentContainer,
          {
            lineOne: mockLine,
          },
          {
            sizing: {
              widthPx: undefined,
              padding: 0,
            },
          },
        );

        testChart.initialChartRender();

        const chartContainerElement = testParentContainer.querySelector(
          'svg.chart-container',
        );
        expect(chartContainerElement).not.toBeNull();

        expect(chartContainerElement!.getAttribute('width')).toEqual(
          `${testWidth}px`,
        );

        const pathContainerElement =
          testParentContainer.querySelector('g.path-container');
        expect(pathContainerElement).not.toBeNull();

        expect(pathContainerElement!.getBoundingClientRect().width).toEqual(
          testWidth,
        );
      });

      it('applies the indicated padding to the plot area container (width)', () => {
        const testWidth = 400;
        const testHeight = testWidth * DEFAULT_HEIGHT_TO_WIDTH_RATIO;
        const padding = 50;

        testParentContainer.style.width = `${testWidth}px`;

        testChart = new LineChart(
          testParentContainer,
          {
            lineOne: mockLine,
          },
          {
            sizing: {
              widthPx: undefined,
              padding,
            },
          },
        );

        testChart.initialChartRender();

        const chartContainerElement = testParentContainer.querySelector(
          'svg.chart-container',
        );
        expect(chartContainerElement).not.toBeNull();

        expect(chartContainerElement!.getAttribute('width')).toEqual(
          `${testWidth}px`,
        );

        const pathContainerElement =
          testParentContainer.querySelector('g.path-container');
        expect(pathContainerElement).not.toBeNull();

        // Width should equal parent width - leftPadding - rightPadding
        expect(pathContainerElement!.getBoundingClientRect().width).toEqual(
          testWidth - padding * 2,
        );

        // Height should equal to:
        // parent width * heithToWidthRatio - leftPadding - rightPadding
        expect(pathContainerElement!.getBoundingClientRect().height).toEqual(
          testHeight - padding * 2,
        );
      });

      it('applies the indicated padding to the plot area container (width & height)', () => {
        const testWidth = 400;
        const heightToWidthRatio = 1;
        const testHeight = 400 * heightToWidthRatio;
        const padding = {
          topPx: 20,
          rightPx: 50,
          bottomPx: 10,
          leftPx: 30,
        };

        testParentContainer.style.width = `${testWidth}px`;

        testChart = new LineChart(
          testParentContainer,
          {
            lineOne: mockLine,
          },
          {
            sizing: {
              widthPx: undefined,
              heightToWidthRatio: 1,
              padding,
            },
          },
        );

        testChart.initialChartRender();

        const chartContainerElement = testParentContainer.querySelector(
          'svg.chart-container',
        );
        expect(chartContainerElement).not.toBeNull();

        expect(chartContainerElement!.getAttribute('width')).toEqual(
          `${testWidth}px`,
        );

        const pathContainerElement =
          testParentContainer.querySelector('g.path-container');
        expect(pathContainerElement).not.toBeNull();

        // Width should equal parent width - leftPadding - rightPadding
        expect(pathContainerElement!.getBoundingClientRect().width).toEqual(
          testWidth - padding.leftPx - padding.rightPx,
        );

        // Height should equal parent height - topPx - bottomPx
        expect(pathContainerElement!.getBoundingClientRect().height).toEqual(
          testHeight - padding.topPx - padding.bottomPx,
        );
      });
    });

    describe('automatic resize', () => {
      it('reacts to parent node size changes and resizes the chart accordingly', async () => {
        const initialParentContainerWidthPx = 400;
        const resultingHeight =
          initialParentContainerWidthPx * DEFAULT_HEIGHT_TO_WIDTH_RATIO;

        testParentContainer.style.width = `${initialParentContainerWidthPx}px`;

        testChart = new LineChart(
          testParentContainer,
          {
            lineOne: mockLine,
          },
          {
            sizing: {
              widthPx: undefined,
              // default value but we want to be epxlicit in tests:
              rerenderOnResize: true,
            },
          },
        );

        testChart.initialChartRender();

        const chartContainerElement = testParentContainer.querySelector(
          'svg.chart-container',
        );
        expect(chartContainerElement).not.toBeNull();

        expect(chartContainerElement!.getAttribute('width')).toEqual(
          `${initialParentContainerWidthPx}px`,
        );

        expect(chartContainerElement!.getAttribute('height')).toEqual(
          `${resultingHeight}px`,
        );

        const newParentContainerWidthPx = 300;
        const newParentContainerHeightPx = 200;

        testParentContainer.style.width = `${newParentContainerWidthPx}px`;
        testParentContainer.style.height = `${newParentContainerHeightPx}px`;

        const newHeight =
          newParentContainerWidthPx * DEFAULT_HEIGHT_TO_WIDTH_RATIO;

        // We simulate the async passage of time for the animations to finish
        await new Promise((resolve) => {
          return setTimeout(resolve, DEFAULT_TRANSITION_TIME_MS);
        });

        expect(chartContainerElement!.getAttribute('width')).toEqual(
          `${newParentContainerWidthPx}px`,
        );

        expect(chartContainerElement!.getAttribute('height')).toEqual(
          `${newHeight}px`,
        );

        testChart.removeEventListeners();
      });
    });
  });

  describe('path rendering', () => {
    it('renders one path', () => {
      testChart = new LineChart(testParentContainer, {
        lineOne: mockLine,
      });

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      const pathOne = chartContainerElement!.querySelector('#lineOne');
      expect(pathOne).not.toBeNull();
    });

    it('renders multiple paths', () => {
      const testChart = new LineChart(testParentContainer, {
        lineOne: mockLine,
        lineTwo: mockLine,
        lineThree: mockLine,
      });

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      const pathOne = chartContainerElement!.querySelector('#lineOne');
      expect(pathOne).not.toBeNull();
      const pathTwo = chartContainerElement!.querySelector('#lineOne');
      expect(pathTwo).not.toBeNull();
      const pathThree = chartContainerElement!.querySelector('#lineOne');
      expect(pathThree).not.toBeNull();
    });

    it('renders a path with the indicated id', () => {
      testChart = new LineChart(
        testParentContainer,
        {
          lineOne: mockLine,
        },
        {
          series: {
            lineOne: {
              id: 'line-one',
            },
          },
        },
      );

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      const pathOne = chartContainerElement!.querySelector('#line-one');
      expect(pathOne).not.toBeNull();
    });

    it('renders a path with the indicated color', () => {
      testChart = new LineChart(
        testParentContainer,
        {
          lineOne: mockLine,
        },
        {
          series: {
            lineOne: {
              id: 'line-one',
              color: 'red',
            },
          },
        },
      );

      testChart.initialChartRender();

      const chartContainerElement = testParentContainer.querySelector('svg');
      expect(chartContainerElement).not.toBeNull();

      const pathOne =
        chartContainerElement!.querySelector<SVGPathElement>('#line-one');
      expect(pathOne).not.toBeNull();

      expect(pathOne!.style.stroke).toEqual('red');
    });

    it('renders two paths with the indicated order', () => {
      const testChart = new LineChart(
        testParentContainer,
        {
          lineOne: mockLine,
          lineTwo: mockLine,
        },
        {
          series: {
            lineOne: {
              id: 'line-one',
              order: 2,
            },
            lineTwo: {
              id: 'line-two',
              order: 1,
            },
          },
        },
      );

      testChart.initialChartRender();

      const pathContainerElement =
        testParentContainer.querySelector<SVGGElement>('g.path-container');
      expect(pathContainerElement).not.toBeNull();

      const children = pathContainerElement!.children;

      // First child should be the one with the lowest order,.
      // It will show behind.
      expect(children.item(0)?.getAttribute('id')).toEqual('line-two');

      // Second child should be the one with the highest order.
      // It will show in front.
      expect(children.item(1)?.getAttribute('id')).toEqual('line-one');
    });

    it('renders two areas with the indicated order', () => {
      const testChart = new LineChart(
        testParentContainer,
        {
          areaOne: mockLine,
          areaTwo: mockLine,
        },
        {
          series: {
            areaOne: {
              id: 'area-one',
              order: 2,
              isArea: true,
            },
            areaTwo: {
              id: 'area-two',
              order: 1,
              isArea: true,
            },
          },
        },
      );

      testChart.initialChartRender();

      const pathContainerElement =
        testParentContainer.querySelector<SVGGElement>('g.path-container');
      expect(pathContainerElement).not.toBeNull();

      const children = pathContainerElement!.children;

      // First child should be the one with the lowest order,.
      // It will show behind.
      expect(children.item(0)?.getAttribute('id')).toEqual('area-two');

      // Second child should be the one with the highest order.
      // It will show in front.
      expect(children.item(1)?.getAttribute('id')).toEqual('area-one');
    });

    it('renders two paths with the indicated coordinates', () => {
      const lineChartSizingConfiguration = {
        widthPx: 200,
        heightToWidthRatio: 1,
        padding: 0,
      };

      const testLine = [
        {
          x: 10,
          y: 20,
        },
        {
          x: 20,
          y: 10,
        },
      ];

      // https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d#path_commands
      const testLinePathCommands = 'M0,0L200,200';

      const testChart = new LineChart(
        testParentContainer,
        {
          lineOne: testLine,
        },
        {
          sizing: lineChartSizingConfiguration,
          series: {
            lineOne: {
              id: 'line-one',
            },
          },
        },
      );

      testChart.initialChartRender();

      const pathContainerElement =
        testParentContainer.querySelector<SVGGElement>('g.path-container');
      expect(pathContainerElement).not.toBeNull();

      const children = pathContainerElement!.children;
      expect(children.length).toEqual(1);

      const pathElement = children.item(0)!;

      expect(pathElement.getAttribute('id')).toEqual('line-one');
      expect(pathElement.getAttribute('d')).toEqual(testLinePathCommands);
    });

    it('renders two areas with the indicated coordinates', () => {
      const lineChartSizingConfiguration = {
        widthPx: 200,
        heightToWidthRatio: 1,
        padding: 0,
      };

      const testLine = [
        {
          x: 10,
          y: 20,
        },
        {
          x: 20,
          y: 10,
        },
      ];

      // https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/d#path_commands
      const testAreaPathCommands = 'M0,0L200,200L200,200L0,200Z';

      const testChart = new LineChart(
        testParentContainer,
        {
          lineOne: testLine,
        },
        {
          sizing: lineChartSizingConfiguration,
          series: {
            lineOne: {
              id: 'area-one',
              isArea: true,
            },
          },
        },
      );

      testChart.initialChartRender();

      const pathContainerElement =
        testParentContainer.querySelector<SVGGElement>('g.path-container');
      expect(pathContainerElement).not.toBeNull();

      const children = pathContainerElement!.children;
      expect(children.length).toEqual(1);

      const pathElement = children.item(0)!;

      expect(pathElement.getAttribute('id')).toEqual('area-one');
      expect(pathElement.getAttribute('d')).toEqual(testAreaPathCommands);
    });
  });
});
