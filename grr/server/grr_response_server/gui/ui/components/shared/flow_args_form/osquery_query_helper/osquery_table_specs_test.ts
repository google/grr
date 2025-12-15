import {allTableSpecs, nameToTable} from './osquery_table_specs';

describe('osquery_table_specs', () => {
  it('parses the table specs file into a variable', () => {
    expect(allTableSpecs.length).toBeGreaterThan(0);
  });

  it("finds a table named 'users'", () => {
    const usersTable = nameToTable('users');

    expect(usersTable).toBeTruthy();
    expect(usersTable?.name).toBeTruthy();
    expect(usersTable?.description).toBeTruthy();
    expect(usersTable?.columns).toBeTruthy();
  });

  it('returns undefined when a table is not found', () => {
    const nonExistingTable = nameToTable(
      'it would be very meta if osquery adds a table with this name',
    );

    expect(nonExistingTable).toBeUndefined();
  });
});
