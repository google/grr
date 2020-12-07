import {Component, Input} from '@angular/core';
import {StringWithHighlightsPart, stringWithHighlightsFromMatch} from '@app/lib/fuzzy_matcher';
import {ValueWithMatchResult} from '../osquery_query_helper';


export declare interface MatchResultForTable {
  name: ValueWithMatchResult;
  description: ValueWithMatchResult;
  columns: ReadonlyArray<ValueWithMatchResult>;
}


/** An item containing table info to display in the query helper menu */
@Component({
  selector: 'table-info-item',
  templateUrl: './table_info_item.ng.html',
  styleUrls: ['./table_info_item.scss'],
})
export class TableInfoItem {
  @Input()
  tableMatchResult?: MatchResultForTable;

  get docsLinkToTable(): string {
    const tableName = this.tableMatchResult?.name.value;
    return `https://osquery.io/schema/4.5.1/#${tableName}`;
  }

  convertToHighlightedParts(
      valueWithMatchResult: ValueWithMatchResult,
  ): ReadonlyArray<StringWithHighlightsPart> {
    if (valueWithMatchResult.matchResult) {
      const stringWithHighlights = stringWithHighlightsFromMatch(
          valueWithMatchResult.matchResult,
      );
      return stringWithHighlights.parts;
    } else {
      return [
        {
          value: valueWithMatchResult.value,
          highlight: false,
        }
      ];
    }
  }

  trackMatchResultByValue(
      _index: number,
      valueWithMatchResult: ValueWithMatchResult,
  ): string {
    return valueWithMatchResult.value;
  }

  trackByIndex(index: number, _element: unknown): number {
    return index;
  }
}
