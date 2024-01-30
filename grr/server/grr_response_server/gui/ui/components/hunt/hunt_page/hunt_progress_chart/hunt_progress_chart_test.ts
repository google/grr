import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../../testing';

import {
  HuntProgressChart,
  HuntProgressLineChartDataset,
} from './hunt_progress_chart';

initTestEnvironment();

@Component({
  template: `<app-hunt-progress-chart
    [chartProgressData]="chartProgressData">
  </app-hunt-progress-chart>`,
})
class TestHostComponent {
  chartProgressData: HuntProgressLineChartDataset | null | undefined = null;
  totalClients: bigint | null | undefined = null;
}

describe('HuntProgressChart Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HuntProgressChart],
      declarations: [TestHostComponent],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('shows a message if hunt completion progress data is null', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.chartProgressData = undefined;

    fixture.detectChanges();

    const noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-chart-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a message if hunt completion progress data is empty', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.chartProgressData = {
      completedClients: [],
      inProgressClients: [],
    };

    fixture.detectChanges();

    const noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-chart-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a message if hunt completion progress data has only 1 data-point', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.chartProgressData = {
      inProgressClients: [{x: 1669026900000, y: 0}],
      completedClients: [{x: 1669026900000, y: 0}],
    };

    fixture.detectChanges();

    const noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-chart-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no progress data to show.',
    );
  });

  it('shows a chart if hunt completion progress data is valid', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    const chartProgressDataMock: HuntProgressLineChartDataset = {
      inProgressClients: [
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 7},
        {x: 1669026900000, y: 29},
      ],
      completedClients: [
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 0},
      ],
    };

    hostComponentInstance.chartProgressData = chartProgressDataMock;

    fixture.detectChanges();

    const chartSvg = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-chart-container svg',
    );

    expect(chartSvg).not.toBeNull();
  });

  it('shows a chart after the completion data gets updated', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.chartProgressData = {
      completedClients: [],
      inProgressClients: [],
    };

    fixture.detectChanges();

    let noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-chart-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no progress data to show.',
    );

    const chartProgressDataMock: HuntProgressLineChartDataset = {
      inProgressClients: [
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 7},
        {x: 1669026900000, y: 29},
      ],
      completedClients: [
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 0},
        {x: 1669026900000, y: 0},
      ],
    };

    hostComponentInstance.chartProgressData = chartProgressDataMock;

    fixture.detectChanges();

    const chartSvg = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-chart-container svg',
    );

    expect(chartSvg).not.toBeNull();
    noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-chart-container .no-data',
    );

    expect(noDataBlock).toBeNull();
  });
});
