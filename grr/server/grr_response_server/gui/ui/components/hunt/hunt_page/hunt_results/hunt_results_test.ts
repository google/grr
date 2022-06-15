import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatTabGroupHarness} from '@angular/material/tabs/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {HuntPageLocalStore, HuntResultsState} from '../../../../store/hunt_page_local_store';
import {mockHuntPageLocalStore} from '../../../../store/hunt_page_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {HuntResults} from './hunt_results';
import {HuntResultsModule} from './module';

initTestEnvironment();

describe('HuntResults', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntResultsModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntPageLocalStore, {useFactory: mockHuntPageLocalStore})
        .compileComponents();
  }));

  it('displays hunt results from store using appropriate components',
     async () => {
       const fixture = TestBed.createComponent(HuntResults);
       const huntPageLocalStore =
           injectMockStore(HuntPageLocalStore, fixture.debugElement);
       fixture.detectChanges();

       expect(huntPageLocalStore.loadMoreResults).toHaveBeenCalled();

       const res: ReadonlyArray<ApiHuntResult> = [
         {clientId: 'C.1234', timestamp: '1234', payloadType: 'foo'},
         {clientId: 'C.5678', timestamp: '5678', payloadType: 'foo'}
       ];
       huntPageLocalStore.mockedObservables.huntResults$.next({
         results: res,
       } as HuntResultsState);

       fixture.detectChanges();

       expect(fixture.nativeElement.textContent).toContain('Results');

       const rows = fixture.nativeElement.querySelectorAll('mat-row');
       expect(rows.length).toBe(2);

       enum CellIndexOf { CLIENT_ID = 0, TIMESTAMP, PAYLOAD_TYPE }

       let cells = rows[0].querySelectorAll('mat-cell');
       expect(cells[CellIndexOf.CLIENT_ID].innerText.trim())
           .toContain('C.1234');
       expect(cells[CellIndexOf.TIMESTAMP]
                  .querySelectorAll('app-timestamp')
                  .length)
           .toBe(1);
       expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
           .toContain('foo');

       cells = rows[1].querySelectorAll('mat-cell');
       expect(cells[CellIndexOf.CLIENT_ID].innerText.trim())
           .toContain('C.5678');
       expect(cells[CellIndexOf.TIMESTAMP]
                  .querySelectorAll('app-timestamp')
                  .length)
           .toBe(1);
       expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
           .toContain('foo');
     });

  it('displays one tab per result type', async () => {
    const fixture = TestBed.createComponent(HuntResults);
    const huntPageLocalStore =
        injectMockStore(HuntPageLocalStore, fixture.debugElement);
    fixture.detectChanges();

    expect(huntPageLocalStore.loadMoreResults).toHaveBeenCalled();

    const res: ReadonlyArray<ApiHuntResult> = [
      {clientId: 'C.1234', payloadType: 'foo'},
      {clientId: 'C.5678', payloadType: 'bar'}
    ];
    huntPageLocalStore.mockedObservables.huntResults$.next({
      results: res,
    } as HuntResultsState);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Results');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const tabGroupHarness = await harnessLoader.getHarness(MatTabGroupHarness);
    expect((await tabGroupHarness.getTabs()).length).toEqual(2);

    const fooTab = (await tabGroupHarness.getTabs({label: 'foo'}))[0];
    await fooTab.select();
    expect(await fooTab.getTextContent()).toContain('C.1234');

    const barTab = (await tabGroupHarness.getTabs({label: 'bar'}))[0];
    await barTab.select();
    expect(await barTab.getTextContent()).toContain('C.5678');
  });

  it('expands translated results', async () => {
    const fixture = TestBed.createComponent(HuntResults);
    const huntPageLocalStore =
        injectMockStore(HuntPageLocalStore, fixture.debugElement);
    fixture.detectChanges();

    expect(huntPageLocalStore.loadMoreResults).toHaveBeenCalled();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.1234',
        payloadType: 'ClientSummary',
        payload: {
          'systemInfo': {fqdn: 'griffindor.pc'},
          'users':
              [{username: 'harry'}, {username: 'ron'}, {username: 'hermione'}]
        }
      },
      {
        clientId: 'C.5678',
        payloadType: 'ClientSummary',
        payload: {
          'systemInfo': {fqdn: 'ravenclaw.pc'},
          'users': [{username: 'luna'}]
        }
      },
      {
        clientId: 'C.999',
        payloadType: 'ClientSummary',
        payload: {},
      },
    ];
    huntPageLocalStore.mockedObservables.huntResults$.next({
      results: res,
    } as HuntResultsState);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Results');

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(3);

    enum CellIndexOf {
      CLIENT_ID = 0,
      TIMESTAMP,
      PAYLOAD_TYPE,
      FQDN,
      NUM_USERS,
      USERNAMES
    }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('griffindor.pc');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('3');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim())
        .toContain('harry, ron, hermione');

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('ravenclaw.pc');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('1');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain('luna');

    cells = rows[2].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.999');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText).toBeFalsy();
    expect(cells[CellIndexOf.NUM_USERS].innerText).toBeFalsy();
    expect(cells[CellIndexOf.USERNAMES].innerText).toBeFalsy();
  });
});
