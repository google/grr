import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {take} from 'rxjs/operators';

import {isNonNull} from '../../../lib/preconditions';
import {initTestEnvironment} from '../../../testing';

import {OsqueryQueryHelperModule} from './module';
import {OsqueryQueryHelper} from './osquery_query_helper';
import {nameToTable} from './osquery_table_specs';

initTestEnvironment();

describe('OsqueryQueryHelper component', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            OsqueryQueryHelperModule,
            NoopAnimationsModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function constructFixture() {
    const fixture = TestBed.createComponent(OsqueryQueryHelper);
    fixture.detectChanges();
    return fixture;
  }

  it('should contain only existing tables in the suggested category', () => {
    const fixture = constructFixture();

    const suggestedTableSpecs =
        fixture.componentInstance.suggestedTableNames.map(nameToTable);

    expect(suggestedTableSpecs.every(isNonNull)).toBeTrue();
  });

  it(
      'should have queryToDisplay$ emit undefined when search is not a valid table name',
      fakeAsync(() => {
        const fixture = constructFixture();

        fixture.componentInstance.searchControl.setValue(
            `fuzzymatchingispowerfulsomakesurethisreturnsnomatches`);
        tick(Infinity);  // For the debounce

        // This relies on the `shareReplay(1)` operator as part of the
        // `searchValues$` pipeline inside `osquery_query_helper.ts`.
        fixture.componentInstance.queryToReturn$.pipe(take(1)).subscribe(
            queryToReturn => {
              expect(queryToReturn).toBeUndefined();
            });
      }),
  );

  it(
      'should have queryToDisplay$ emit proper string when search is a valid table name',
      fakeAsync(() => {
        const fixture = constructFixture();

        // Assumes that table "users" exists
        fixture.componentInstance.searchControl.setValue(`users`);
        tick(Infinity);  // For the debounce

        // This relies on the `shareReplay(1)` operator as part of the
        // `searchValues$` pipeline inside `osquery_query_helper.ts`.
        fixture.componentInstance.queryToReturn$.pipe(take(1)).subscribe(
            queryToReturn => {
              expect(queryToReturn).toBeDefined();
              expect(queryToReturn).toBeInstanceOf(String);
            });
      }),
  );

  it(
      'should have no elements in filteredCategories$ when search doesn\'t match anything',
      fakeAsync(() => {
        const fixture = constructFixture();

        fixture.componentInstance.searchControl.setValue(
            `fuzzymatchingispowerfulsomakesurethisreturnsnomatches`);
        tick(Infinity);  // For the debounce

        // This relies on the `shareReplay(1)` operator as part of the
        // `searchValues$` pipeline inside `osquery_query_helper.ts`.
        fixture.componentInstance.filteredCategories$.pipe(take(1)).subscribe(
            categoriesList => {
              expect(categoriesList.length).toBe(0);
            });
      }),
  );

  it(
      'should have some elements in filteredCategories$ when search matches table names',
      fakeAsync(() => {
        const fixture = constructFixture();

        // Assumes that table "users" exists
        fixture.componentInstance.searchControl.setValue(`users`);
        tick(Infinity);  // For the debounce

        // This relies on the `shareReplay(1)` operator as part of the
        // `searchValues$` pipeline inside `osquery_query_helper.ts`.
        fixture.componentInstance.filteredCategories$.pipe(take(1)).subscribe(
            categoriesList => {
              expect(categoriesList.length).toBeGreaterThan(0);
            });
      }),
  );
});
