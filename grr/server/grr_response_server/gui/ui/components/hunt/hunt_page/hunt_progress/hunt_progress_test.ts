import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {newHunt} from '../../../../lib/models/model_test_util';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {HuntPageGlobalStoreMock, mockHuntPageGlobalStore} from '../../../../store/hunt_page_global_store_test_util';
import {STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {HuntProgress} from './hunt_progress';
import {HuntProgressModule} from './module';

initTestEnvironment();

describe('HuntProgress Component', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntProgressModule,
            RouterTestingModule,
          ],
          providers: [...STORE_PROVIDERS],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntPageGlobalStore, {useFactory: () => huntPageGlobalStore})
        .compileComponents();
  }));

  it('displays card title', () => {
    const fixture = TestBed.createComponent(HuntProgress);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Total progress');
    expect(fixture.nativeElement.textContent).toContain('~ unknown clients');
  });

  it('displays summaries based on store', () => {
    const fixture = TestBed.createComponent(HuntProgress);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      allClientsCount: BigInt(100),
      completedClientsCount: BigInt(3),
      remainingClientsCount: BigInt(25),
      clientsWithResultsCount: BigInt(1),
      crashedClientsCount: BigInt(2),
      failedClientsCount: BigInt(3),
    }));
    fixture.detectChanges();

    const summaries = fixture.nativeElement.querySelectorAll('.summary');
    expect(summaries.length).toBe(5);

    expect(summaries[0].children[0].innerText).toContain('Complete');
    expect(summaries[0].children[1].innerText).toContain('3 %');
    expect(summaries[0].children[2].innerText).toContain('3 clients');

    expect(summaries[1].children[0].innerText).toContain('In progress');
    expect(summaries[1].children[1].innerText).toContain('25 %');
    expect(summaries[1].children[2].innerText).toContain('25 clients');

    expect(summaries[2].children[0].innerText).toContain('Without results');
    expect(summaries[2].children[1].innerText).toContain('2 %');
    expect(summaries[2].children[2].innerText).toContain('2 clients');

    expect(summaries[3].children[0].innerText).toContain('With results');
    expect(summaries[3].children[1].innerText).toContain('1 %');
    expect(summaries[3].children[2].innerText).toContain('1 client');

    expect(summaries[4].children[0].innerText).toContain('Errors and Crashes');
    expect(summaries[4].children[1].innerText).toContain('5 %');
    expect(summaries[4].children[2].innerText).toContain('5 clients');
  });

  it('does not show negative numbers', () => {
    const fixture = TestBed.createComponent(HuntProgress);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
      allClientsCount: BigInt(100),
      completedClientsCount: BigInt(-3),
      remainingClientsCount: BigInt(-25),
      clientsWithResultsCount: BigInt(-1),
      crashedClientsCount: BigInt(-2),
      failedClientsCount: BigInt(-3),
    }));
    fixture.detectChanges();

    const summaries = fixture.nativeElement.querySelectorAll('.summary');
    expect(summaries.length).toBe(5);

    expect(summaries[0].children[0].innerText).toContain('Complete');
    expect(summaries[0].children[1].innerText).toContain('0 %');
    expect(summaries[0].children[2].innerText).toContain('0 clients');

    expect(summaries[1].children[0].innerText).toContain('In progress');
    expect(summaries[1].children[1].innerText).toContain('0 %');
    expect(summaries[1].children[2].innerText).toContain('0 clients');

    expect(summaries[2].children[0].innerText).toContain('Without results');
    expect(summaries[2].children[1].innerText).toContain('0 %');
    expect(summaries[2].children[2].innerText).toContain('0 clients');

    expect(summaries[3].children[0].innerText).toContain('With results');
    expect(summaries[3].children[1].innerText).toContain('0 %');
    expect(summaries[3].children[2].innerText).toContain('0 client');

    expect(summaries[4].children[0].innerText).toContain('Errors and Crashes');
    expect(summaries[4].children[1].innerText).toContain('0 %');
    expect(summaries[4].children[2].innerText).toContain('0 clients');
  });

  describe('Hunt progress table', () => {
    it('does not show the hunt progress table data when there is no hunt',
       () => {
         const fixture = TestBed.createComponent(HuntProgress);
         fixture.detectChanges();

         huntPageGlobalStore.mockedObservables.selectedHunt$.next(null);

         huntPageGlobalStore.mockedObservables.huntProgress$.next({
           startPoints: [
             {
               xValue: 1678379900,
               yValue: 10,
             },
           ],
           completePoints: [
             {
               xValue: 1678379900,
               yValue: 5,
             },
           ],
         });

         fixture.detectChanges();

         const table = fixture.nativeElement.querySelector(
             'app-hunt-progress-table mat-table');

         expect(table).toBeNull();
       });

    it('does not show the hunt progress table data when there is no hunt progress data',
       () => {
         const fixture = TestBed.createComponent(HuntProgress);
         fixture.detectChanges();

         huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
           allClientsCount: BigInt(0),
         }));

         huntPageGlobalStore.mockedObservables.huntProgress$.next(undefined);

         fixture.detectChanges();

         const table = fixture.nativeElement.querySelector(
             'app-hunt-progress-table mat-table');

         expect(table).toBeNull();
       });

    it('shows the hunt progress table data without percentages', () => {
      const fixture = TestBed.createComponent(HuntProgress);
      fixture.detectChanges();

      huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
        allClientsCount: BigInt(0),
      }));

      huntPageGlobalStore.mockedObservables.huntProgress$.next({
        startPoints: [
          {
            xValue: 1678379900,
            yValue: 10,
          },
        ],
        completePoints: [
          {
            xValue: 1678379900,
            yValue: 5,
          },
        ],
      });

      fixture.detectChanges();

      const table = fixture.nativeElement.querySelector(
          'app-hunt-progress-table mat-table');

      expect(table).not.toBeNull();

      const rows =
          table.querySelectorAll('app-hunt-progress-table mat-table mat-row');

      expect(rows.length).toEqual(1);

      const cells = rows[0].querySelectorAll('mat-cell');

      expect(cells[0].textContent).toContain('2023-03-09 16:43:20 UTC');
      expect(cells[1].innerText).toEqual('5');
      expect(cells[2].innerText).toEqual('10');
    });

    it('shows the hunt progress table data with percentages', () => {
      const fixture = TestBed.createComponent(HuntProgress);
      fixture.detectChanges();

      huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
        allClientsCount: BigInt(10),
      }));

      huntPageGlobalStore.mockedObservables.huntProgress$.next({
        startPoints: [
          {
            xValue: 1678379900,
            yValue: 10,
          },
        ],
        completePoints: [
          {
            xValue: 1678379900,
            yValue: 5,
          },
        ],
      });

      fixture.detectChanges();

      const table = fixture.nativeElement.querySelector(
          'app-hunt-progress-table mat-table');

      expect(table).not.toBeNull();

      const rows =
          table.querySelectorAll('app-hunt-progress-table mat-table mat-row');

      expect(rows.length).toEqual(1);

      const cells = rows[0].querySelectorAll('mat-cell');

      expect(cells[0].textContent).toContain('2023-03-09 16:43:20 UTC');
      expect(cells[1].textContent.trim()).toEqual('5 (50%)');
      expect(cells[2].textContent.trim()).toEqual('10 (100%)');
    });

    it('Groups multiple data-points into one, as they are within 5 minutes',
       () => {
         const fixture = TestBed.createComponent(HuntProgress);
         fixture.detectChanges();

         huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
           allClientsCount: BigInt(30),
         }));

         huntPageGlobalStore.mockedObservables.huntProgress$.next({
           startPoints: [
             {
               xValue: 1678379900,
               yValue: 10,
             },
             {
               xValue: 1678379910,
               yValue: 25,
             },
             {
               xValue: 1678379920,
               yValue: 30,
             },
           ],
           completePoints: [
             {
               xValue: 1678379900,
               yValue: 5,
             },
             {
               xValue: 1678379910,
               yValue: 20,
             },
             {
               xValue: 1678379920,
               yValue: 30,
             },
           ],
         });

         fixture.detectChanges();

         const table = fixture.nativeElement.querySelector(
             'app-hunt-progress-table mat-table');

         expect(table).not.toBeNull();

         const rows = table.querySelectorAll(
             'app-hunt-progress-table mat-table mat-row');

         expect(rows.length).toEqual(1);

         const cells = rows[0].querySelectorAll('mat-cell');

         expect(cells[0].textContent).toContain('2023-03-09 16:43:20 UTC');
         expect(cells[1].textContent.trim()).toEqual('30 (100%)');
         expect(cells[2].textContent.trim()).toEqual('30 (100%)');
       });

    it('Groups multiple data-points into 2 groups, as they are not within 5 minutes',
       () => {
         const fixture = TestBed.createComponent(HuntProgress);
         fixture.detectChanges();

         huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
           allClientsCount: BigInt(30),
         }));

         huntPageGlobalStore.mockedObservables.huntProgress$.next({
           startPoints: [
             {
               xValue: 1678379900,
               yValue: 10,
             },
             {
               xValue: 1678379910,
               yValue: 25,
             },
             {
               xValue: 1678389920,
               yValue: 30,
             },
           ],
           completePoints: [
             {
               xValue: 1678379900,
               yValue: 5,
             },
             {
               xValue: 1678379910,
               yValue: 20,
             },
             {
               xValue: 1678389920,
               yValue: 30,
             },
           ],
         });

         fixture.detectChanges();

         const table = fixture.nativeElement.querySelector(
             'app-hunt-progress-table mat-table');

         expect(table).not.toBeNull();

         const rows = table.querySelectorAll(
             'app-hunt-progress-table mat-table mat-row');

         expect(rows.length).toEqual(2);

         let rowCells = rows[0].querySelectorAll('mat-cell');

         expect(rowCells[0].textContent).toContain('2023-03-09 16:43:20 UTC');
         expect(rowCells[1].textContent.trim()).toEqual('20 (66%)');
         expect(rowCells[2].textContent.trim()).toEqual('25 (83%)');

         rowCells = rows[1].querySelectorAll('mat-cell');

         expect(rowCells[0].textContent).toContain('2023-03-09 19:28:20 UTC');
         expect(rowCells[1].textContent.trim()).toEqual('30 (100%)');
         expect(rowCells[2].textContent.trim()).toEqual('30 (100%)');
       });

    it('Does not group data-points, as none are within 5 minutes', () => {
      const fixture = TestBed.createComponent(HuntProgress);
      fixture.detectChanges();

      huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
        allClientsCount: BigInt(30),
      }));

      huntPageGlobalStore.mockedObservables.huntProgress$.next({
        startPoints: [
          {
            xValue: 1678369900,
            yValue: 10,
          },
          {
            xValue: 1678379910,
            yValue: 25,
          },
          {
            xValue: 1678389920,
            yValue: 30,
          },
        ],
        completePoints: [
          {
            xValue: 1678369900,
            yValue: 5,
          },
          {
            xValue: 1678379910,
            yValue: 20,
          },
          {
            xValue: 1678389920,
            yValue: 30,
          },
        ],
      });

      fixture.detectChanges();

      const table = fixture.nativeElement.querySelector(
          'app-hunt-progress-table mat-table');

      expect(table).not.toBeNull();

      const rows =
          table.querySelectorAll('app-hunt-progress-table mat-table mat-row');

      expect(rows.length).toEqual(3);

      let rowCells = rows[0].querySelectorAll('mat-cell');

      expect(rowCells[0].textContent).toContain('2023-03-09 13:56:40 UTC');
      expect(rowCells[1].textContent.trim()).toEqual('5 (16%)');
      expect(rowCells[2].textContent.trim()).toEqual('10 (33%)');

      rowCells = rows[1].querySelectorAll('mat-cell');

      expect(rowCells[0].textContent).toContain('2023-03-09 16:41:40 UTC');
      expect(rowCells[1].textContent.trim()).toEqual('20 (66%)');
      expect(rowCells[2].textContent.trim()).toEqual('25 (83%)');

      rowCells = rows[2].querySelectorAll('mat-cell');

      expect(rowCells[0].textContent).toContain('2023-03-09 19:26:40 UTC');
      expect(rowCells[1].textContent.trim()).toEqual('30 (100%)');
      expect(rowCells[2].textContent.trim()).toEqual('30 (100%)');
    });

    it('Displays the available information in case of uneven completed and started progress information',
       () => {
         const fixture = TestBed.createComponent(HuntProgress);
         fixture.detectChanges();

         huntPageGlobalStore.mockedObservables.selectedHunt$.next(newHunt({
           allClientsCount: BigInt(30),
         }));

         huntPageGlobalStore.mockedObservables.huntProgress$.next({
           startPoints: [
             {
               xValue: 1678379900,
               yValue: 10,
             },
             {
               xValue: 1678379910,
               yValue: 25,
             },
             {
               xValue: 1678389920,
               yValue: 30,
             },
           ],
           completePoints: [
             {
               xValue: 1678379900,
               yValue: 5,
             },
             {
               xValue: 1678379910,
               yValue: 20,
             },
           ],
         });

         fixture.detectChanges();

         const table = fixture.nativeElement.querySelector(
             'app-hunt-progress-table mat-table');

         expect(table).not.toBeNull();

         const rows = table.querySelectorAll(
             'app-hunt-progress-table mat-table mat-row');

         expect(rows.length).toEqual(2);

         let rowCells = rows[0].querySelectorAll('mat-cell');

         expect(rowCells[0].textContent).toContain('2023-03-09 16:43:20 UTC');
         expect(rowCells[1].textContent.trim()).toEqual('20 (66%)');
         expect(rowCells[2].textContent.trim()).toEqual('25 (83%)');

         rowCells = rows[1].querySelectorAll('mat-cell');

         expect(rowCells[0].textContent).toContain('2023-03-09 19:28:20 UTC');
         expect(rowCells[1].textContent.trim()).toEqual('');
         expect(rowCells[2].textContent.trim()).toEqual('30 (100%)');
       });
  });
});
