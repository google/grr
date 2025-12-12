import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';

import {
  OsqueryQueryHelper,
  SUGGESTED_TABLE_NAMES,
} from './osquery_query_helper';
import {nameToTable, OsqueryTableSpec} from './osquery_table_specs';

initTestEnvironment();

describe('OsqueryQueryHelper component', () => {
  beforeEach(waitForAsync(() => {
    return TestBed.configureTestingModule({
      imports: [OsqueryQueryHelper, NoopAnimationsModule],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  function constructFixture() {
    const fixture = TestBed.createComponent(OsqueryQueryHelper);
    fixture.detectChanges();
    return fixture;
  }

  it('should contain only existing tables in the suggested category', () => {
    const suggestedTableSpecs = SUGGESTED_TABLE_NAMES.map(nameToTable);

    expect(
      suggestedTableSpecs.every(
        (tableSpec: OsqueryTableSpec | undefined) => tableSpec != null,
      ),
    ).toBeTrue();
  });

  it('should set queryToReturn to undefined when search is not a valid table name', fakeAsync(() => {
    const fixture = constructFixture();

    fixture.componentInstance.searchControl.setValue(
      `fuzzymatchingispowerfulsomakesurethisreturnsnomatches`,
    );

    const queryToReturn = fixture.componentInstance.queryToReturn();
    expect(queryToReturn).toBeUndefined();
  }));

  it('should set queryToReturn to proper string when search is a valid table name', fakeAsync(() => {
    const fixture = constructFixture();

    // Assumes that table "users" exists
    fixture.componentInstance.searchControl.setValue(`users`);

    const queryToReturn = fixture.componentInstance.queryToReturn();
    expect(queryToReturn).toBeDefined();
    expect(queryToReturn).toBeInstanceOf(String);
  }));

  it("should have no elements in filteredCategories$ when search doesn't match anything", fakeAsync(() => {
    const fixture = constructFixture();

    fixture.componentInstance.searchControl.setValue(
      `fuzzymatchingispowerfulsomakesurethisreturnsnomatches`,
    );

    const filteredCategories = fixture.componentInstance.filteredCategories();
    expect(filteredCategories).toBeDefined();
    expect(filteredCategories.length).toBe(0);
  }));

  it('should have some elements in filteredCategories when search matches table names', fakeAsync(() => {
    const fixture = constructFixture();

    // Assumes that table "users" exists
    fixture.componentInstance.searchControl.setValue(`users`);

    const filteredCategories = fixture.componentInstance.filteredCategories();
    expect(filteredCategories).toBeDefined();
    expect(filteredCategories.length).toBeGreaterThan(0);
  }));
});
