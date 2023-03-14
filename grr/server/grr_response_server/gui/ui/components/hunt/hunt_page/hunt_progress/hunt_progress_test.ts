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
});
