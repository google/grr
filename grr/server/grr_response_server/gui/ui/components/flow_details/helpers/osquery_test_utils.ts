import { OsqueryColumn, OsqueryRow } from '@app/lib/api/api_interfaces';
import { newFlowListEntry, newFlowResultSet } from '@app/lib/models/model_test_util';
import { DeepMutable } from '@app/lib/type_utils';
import { FlowListEntry, FlowState, FlowResultSet } from '@app/lib/models/flow';
import { DebugElement } from '@angular/core';
import { By } from '@angular/platform-browser';

type FullMutableOsqueryTable = {
  query: string,
  header: {
    columns: ReadonlyArray<OsqueryColumn>,
  },
  rows: ReadonlyArray<OsqueryRow>
};

function newOsqueryTable(): FullMutableOsqueryTable {
  return {
    query: '',
    header: {
      columns: [] as ReadonlyArray<OsqueryColumn>,
    },
    rows: [] as ReadonlyArray<OsqueryRow>,
  };
}

export class OsqueryTableBuilder {
  private table?: FullMutableOsqueryTable;

  withColumns(columns: ReadonlyArray<string>): OsqueryTableBuilder {
    if (this.table === undefined) {
      this.table = newOsqueryTable();
    }

    this.table.header.columns = columns.map((colName) => ({name: colName}));
    return this;
  }

  withValues(values: ReadonlyArray<ReadonlyArray<string>>): OsqueryTableBuilder {
    if (this.table === undefined) {
      this.table = newOsqueryTable();
    }

    this.table.rows = values.map((rowValues) => ({values: rowValues}));
    return this;
  }

  withQuery(query: string) : OsqueryTableBuilder {
    if (this.table === undefined) {
      this.table = newOsqueryTable();
    }

    this.table.query = query;

    return this;
  }

  withQueryIfDefined(query: string): OsqueryTableBuilder {
    if (this.table !== undefined) {
      this.table.query = query;
    }

    return this;
  }

  build(): FullMutableOsqueryTable | undefined {
    return this.table;
  }

  buildWithQueryIfDefined(query: string): FullMutableOsqueryTable | undefined {
    this.withQueryIfDefined(query);
    return this.build();
  }
}

/** Helper class to build a FlowListEntry objects in a declarative manner */
export class OsqueryFlowListEntryBuilder {
  private flowListEntry = newFlowListEntry({args: {query: ''}})  as DeepMutable<FlowListEntry>;

  private query = '';

  private stderr = '';
  private resultsTableBuilder = new OsqueryTableBuilder();

  private progressRowsCount = 0;
  private progressTableBuilder = new OsqueryTableBuilder();

  withFlowState(state: FlowState): OsqueryFlowListEntryBuilder {
    this.flowListEntry.flow.state = state;
    return this;
  }

  withQuery(query: string): OsqueryFlowListEntryBuilder {
    this.query = query;
    return this;
  }

  withStderr(stderr: string): OsqueryFlowListEntryBuilder {
    this.stderr = stderr;
    return this;
  }

  withResultsTable(columns: ReadonlyArray<string>, values: ReadonlyArray<ReadonlyArray<string>>): OsqueryFlowListEntryBuilder {
    this.resultsTableBuilder
      .withColumns(columns)
      .withValues(values);
    return this;
  }

  withProgressTable(
    columns: ReadonlyArray<string>,
    values: ReadonlyArray<ReadonlyArray<string>>
  ): OsqueryFlowListEntryBuilder {
    this.progressTableBuilder
      .withColumns(columns)
      .withValues(values);
    return this;
  }

  withProgressRowsCount(count: number): OsqueryFlowListEntryBuilder {
    this.progressRowsCount = count;
    return this;
  }

  build(): FlowListEntry {
    this.includeResultSet();
    this.includeProgress();
    this.setFlowArgsQuery(this.query);
    return this.flowListEntry as FlowListEntry;
  }

  private setFlowArgsQuery(query: string): void {
    if (this.flowListEntry.flow.args instanceof Object) {
      this.flowListEntry.flow.args = {
        ...this.flowListEntry.flow.args,
        query,
      };
    } else {
      this.flowListEntry.flow.args = { query };
    }
  }

  private includeResultSet(): void {
    const payload = {
      stderr: this.stderr,
      table: this.resultsTableBuilder.buildWithQueryIfDefined(this.query),
    }
    this.flowListEntry.resultSets = [
      newFlowResultSet(payload) as DeepMutable<FlowResultSet>,
    ];
  }

  private includeProgress(): void {
    const progress = {
      totalRowsCount: this.progressRowsCount,
      partialTable: this.progressTableBuilder.buildWithQueryIfDefined(this.query),
    };
    this.flowListEntry.flow.progress = progress;
  }
}

export function elementBySelector(selector: string, root: DebugElement): DebugElement {
  return root?.query(By.css(selector));
}

export function innerText(ofElement: DebugElement) {
  return ofElement?.nativeElement.innerText;
}

export function manyElementsBySelector(selector: string, root: DebugElement): DebugElement[] {
  return root?.queryAll(By.css(selector));
}

/** Helper data structure to parse an osquery_results_table */
export class ParsedDetailsTable {
  queryDiv = elementBySelector('.results-query-text', this.rootElement);
  queryText = innerText(this.queryDiv);

  columnElements = manyElementsBySelector('th', this.rootElement);
  columnsText = this.columnElements.map(columnElement => innerText(columnElement));

  cellDivs = manyElementsBySelector('td', this.rootElement);
  cellsText = this.cellDivs.map(cellDiv => innerText(cellDiv));

  constructor(private readonly rootElement: DebugElement) { }
}

/** Helper data structure to parse and expose all elements of interest from the OsqueryDetails DOM */
export class ParsedOsqueryDetails {
  inProgressDiv = elementBySelector('.in-progress', this.rootElement);
  inProgressText = innerText(this.inProgressDiv);

  errorDiv = elementBySelector('.error', this.rootElement);
  stdErrDiv = elementBySelector('div', this.errorDiv);
  stdErrText = innerText(this.stdErrDiv);

  resultsTableDiv = elementBySelector('.results-table', this.rootElement);

  progressTableDiv = elementBySelector('.progress-table', this.rootElement);

  showAdditionalDiv = elementBySelector('.show-additional', this.progressTableDiv);

  showAdditionalTextDiv = elementBySelector('.show-additional-text', this.showAdditionalDiv);
  showAdditionalTextText = innerText(this.showAdditionalTextDiv);

  showAdditionalButton = elementBySelector('button', this.showAdditionalDiv);

  constructor(private readonly rootElement: DebugElement) { }
}
