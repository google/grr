import {newOsqueryColumnSpec, newOsqueryTableSpec} from './osquery_table_specs';
import {constructSelectAllFromTable} from './query_composer';

describe('QueryComposer', () => {
  it("shouldn't add a WHERE clause if there are no required fields", () => {
    const tableSpec = newOsqueryTableSpec({
      columns: [
        newOsqueryColumnSpec({
          required: false,
        }),
      ],
    });

    const query = constructSelectAllFromTable(tableSpec);

    expect(query).not.toContain('WHERE');
  });

  it('should add an an indented WHERE clause if there is a required filed', () => {
    const tableSpec = newOsqueryTableSpec({
      columns: [
        newOsqueryColumnSpec({
          name: 'not_required',
          required: false,
        }),
        newOsqueryColumnSpec({
          name: 'required_column',
          required: true,
        }),
      ],
    });

    const query = constructSelectAllFromTable(tableSpec);
    expect(query).toContain("WHERE\n\trequired_column = ''");
  });

  it('should add an indented SELECT clause with all the column names', () => {
    const tableSpec = newOsqueryTableSpec({
      columns: [
        newOsqueryColumnSpec({
          name: 'first_column',
        }),
        newOsqueryColumnSpec({
          name: 'second_column',
        }),
      ],
    });

    const query = constructSelectAllFromTable(tableSpec);

    expect(query).toContain('SELECT\n\tfirst_column,\n\tsecond_column');
  });

  it('should add a semicolon at the end', () => {
    const tableSpec = newOsqueryTableSpec();

    const query = constructSelectAllFromTable(tableSpec);

    expect(query.slice(-1)).toBe(';');
  });
});
