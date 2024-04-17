import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component, ViewChild} from '@angular/core';
import {TestBed, fakeAsync, tick, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {MatTabGroupHarness} from '@angular/material/tabs/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiHuntError, ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {HttpApiService} from '../../../../lib/api/http_api_service';
import {mockHttpApiService} from '../../../../lib/api/http_api_service_test_util';
import {
  HuntResultsTableTabConfig,
  PayloadType,
  TypedHuntResultOrError,
} from '../../../../lib/models/result';
import {STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {HuntResults} from './hunt_results';
import {HuntResultsModule} from './module';

initTestEnvironment();

@Component({
  template: `<app-hunt-results
      [huntId]="huntId"
      [tabsConfig]="tabsConfig"
      [isLoading]="isLoading"
      (selectedHuntResult)="selectedHuntResult($event)">
    </app-hunt-results>`,
})
class TestHostComponent {
  huntId: string | undefined = undefined;
  tabsConfig: HuntResultsTableTabConfig[] | undefined = undefined;
  isLoading: boolean | undefined = undefined;

  @ViewChild(HuntResults) huntResults!: HuntResults;

  selectedHuntResult(details: TypedHuntResultOrError): void {}
}

describe('HuntResults', () => {
  // We mock the HttpApiService to be able to populate the Hunt Results Table.
  const httpApiService = mockHttpApiService();

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, HuntResultsModule],
      providers: [
        ...STORE_PROVIDERS,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      declarations: [TestHostComponent],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('Shows title and "Nothing to show" if no results are available', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = '1984';
    component.tabsConfig = [];

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Results');

    const noDataBlock = fixture.debugElement.query(By.css('.no-data'));

    expect(noDataBlock).toBeTruthy();
    expect(noDataBlock.nativeElement.textContent).toContain('Nothing to show');
  });

  it('does NOT display download button when no data', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = 'XXX';
    component.tabsConfig = [];
    fixture.detectChanges();

    const downloadButton = fixture.debugElement.query(
      By.css('#downloadButton'),
    );
    expect(downloadButton).toBeFalsy();
    expect(fixture.nativeElement.textContent).not.toContain('Download');
  });

  it('displays download button', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = 'XXX';
    component.tabsConfig = [
      {
        tabName: 'File finder',
        totalResultsCount: 10,
        payloadType: PayloadType.FILE_FINDER_RESULT,
      },
    ];

    fixture.detectChanges();

    const downloadButton = fixture.debugElement.query(
      By.css('#downloadButton'),
    );
    expect(downloadButton).toBeTruthy();

    const primaryOption = downloadButton.query(By.css('a'));
    expect(primaryOption).toBeTruthy();
    expect(primaryOption.attributes['href']).toContain(
      'hunts/XXX/results/files-archive?archive_format=TAR_GZ',
    );

    const openMenuButton = downloadButton.query(By.css('button'));
    expect(openMenuButton).toBeTruthy();
    await openMenuButton.nativeElement.click();
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    const renderedMenuItems = await menu.getItems();

    expect(renderedMenuItems.length).toBe(4);
    expect(await renderedMenuItems[0].getText()).toContain('ZIP');
    expect(await renderedMenuItems[1].getText()).toContain('CSV');
    expect(await renderedMenuItems[2].getText()).toContain('YAML');
    expect(await renderedMenuItems[3].getText()).toContain('SQL');
  });

  it('displays message when no data', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = 'XXX';
    component.tabsConfig = [];
    component.isLoading = false;

    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nothing to show');
  });

  it('does NOT display message when there is any data', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = 'XXX';
    component.tabsConfig = [
      {
        tabName: 'File finder',
        totalResultsCount: 10,
        payloadType: PayloadType.FILE_FINDER_RESULT,
      },
    ];

    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Nothing to show');
  });

  describe('Selected Hunt Result emission', () => {
    it('emits the selected Hunt result', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.huntId = '1984';
      component.tabsConfig = [];

      fixture.detectChanges();

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      const mockResult: ApiHuntResult = {
        'clientId': 'C.1234',
        'payload': {
          'foo': 'bar',
        },
        'payloadType': PayloadType.USER,
        'timestamp': '1',
      };

      // We simulated an event emitted by the Hunt Result Tables:
      component.huntResults.emitSelectedHuntResult(
        mockResult,
        PayloadType.USER,
      );

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockResult,
        payloadType: PayloadType.USER,
      });
    });

    it('emits the selected Hunt result after selecting it by clicking', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.huntId = '1984';
      component.tabsConfig = [
        {
          tabName: 'User',
          totalResultsCount: 1,
          payloadType: PayloadType.USER,
        },
      ];

      fixture.detectChanges();

      const mockHuntResult = {
        'clientId': 'C.1234',
        'payload': {
          'foo': 'bar',
        },
        'payloadType': PayloadType.USER,
        'timestamp': '1',
      };

      // We provide a mock response for the Hunt Results Local Store:
      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('View details');

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      fixture.nativeElement.querySelector('.view-details-button').click();

      fixture.detectChanges();

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockHuntResult,
        payloadType: PayloadType.USER,
      });
    });

    it('emits the selected Hunt error', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.huntId = '1984';
      component.tabsConfig = [];

      fixture.detectChanges();

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      const mockError: ApiHuntError = {
        clientId: 'C.1234',
        logMessage: 'foo',
        backtrace: 'bar',
        timestamp: '1',
      };

      // We simulated an event emitted a Hunt Error Table:
      component.huntResults.emitSelectedHuntResult(
        mockError,
        PayloadType.API_HUNT_ERROR,
      );

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockError,
        payloadType: PayloadType.API_HUNT_ERROR,
      });
    });

    it('emits the selected Hunt result after selecting it by clicking', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.huntId = '1984';
      component.tabsConfig = [
        {
          tabName: 'Errors',
          totalResultsCount: 1,
          payloadType: PayloadType.API_HUNT_ERROR,
        },
      ];

      fixture.detectChanges();

      const mockHuntError: ApiHuntError = {
        clientId: 'C.mockClientId',
        timestamp: '1669027009243432',
        backtrace: 'fooTrace',
        logMessage: 'Something went wrong.',
      };

      // We provide a mock response to populate the Hunt Results Table:
      httpApiService.mockedObservables.listErrorsForHunt.next([mockHuntError]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('View details');

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      fixture.nativeElement.querySelector('.view-details-button').click();

      fixture.detectChanges();

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockHuntError,
        payloadType: PayloadType.API_HUNT_ERROR,
      });
    });
  });

  describe('Loading states', () => {
    it('Does not show loading spinner if results count are not loading', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.isLoading = false;
      component.tabsConfig = [];
      fixture.detectChanges();

      const loadingSpinner = fixture.debugElement.query(By.css('mat-spinner'));

      expect(loadingSpinner).toBeNull();
    });

    it('Shows loading spinner if results count are loading', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.isLoading = true;
      component.tabsConfig = [];
      fixture.detectChanges();

      const loadingSpinner = fixture.debugElement.query(By.css('mat-spinner'));

      expect(loadingSpinner).toBeTruthy();
    });
  });

  describe('Result Table tabs', () => {
    it('displays one tab per result type', fakeAsync(async () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.huntId = 'XXX';
      component.tabsConfig = [
        {
          tabName: 'File finder',
          totalResultsCount: 10,
          payloadType: PayloadType.FILE_FINDER_RESULT,
        },
        {
          tabName: 'User',
          totalResultsCount: 5,
          payloadType: PayloadType.USER,
        },
      ];

      fixture.detectChanges();

      // We mock an empty list of results as a response for the Hunt Results
      // Table.
      httpApiService.mockedObservables.listResultsForHunt.next([]);

      tick();
      fixture.detectChanges();

      const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
      const tabGroupHarness =
        await harnessLoader.getHarness(MatTabGroupHarness);
      expect((await tabGroupHarness.getTabs()).length).toEqual(2);

      const fileFinderTab = (
        await tabGroupHarness.getTabs({label: 'File finder'})
      )[0];
      expect(fileFinderTab).toBeTruthy();

      await fileFinderTab.select();
      expect(await fileFinderTab.getTextContent()).toContain(
        `${PayloadType.FILE_FINDER_RESULT} results could not be loaded.`,
      );

      const userTab = (await tabGroupHarness.getTabs({label: 'User'}))[0];
      expect(userTab).toBeTruthy();

      await userTab.select();
      expect(await userTab.getTextContent()).toContain(
        `${PayloadType.USER} results could not be loaded.`,
      );
    }));
  });

  it('displays the Error tab with its icon', fakeAsync(async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const component = fixture.componentInstance;

    component.huntId = 'XXX';
    component.tabsConfig = [
      {
        tabName: 'Errors',
        totalResultsCount: 1,
        payloadType: PayloadType.API_HUNT_ERROR,
      },
    ];

    fixture.detectChanges();

    // We mock an empty list of results as a response for the Hunt Results
    // Table.
    httpApiService.mockedObservables.listErrorsForHunt.next([]);

    tick();
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const tabGroupHarness = await harnessLoader.getHarness(MatTabGroupHarness);
    expect((await tabGroupHarness.getTabs()).length).toEqual(1);

    // We can't access the MatTabLabel native element through the harness,
    // so we do a normal query to check if the warning icon is present.
    const errorsTabLabel = fixture.debugElement.query(
      By.css('.mdc-tab__text-label'),
    );
    expect(errorsTabLabel).toBeTruthy();

    expect(errorsTabLabel.nativeElement.textContent).toContain('Errors');
    const warningIcon = errorsTabLabel.query(By.css('mat-icon'));

    expect(warningIcon).toBeTruthy();
    expect(warningIcon.nativeElement.textContent).toContain('warning');
  }));
});
