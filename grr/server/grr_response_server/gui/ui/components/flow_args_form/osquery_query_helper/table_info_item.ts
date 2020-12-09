import {Component, Input} from '@angular/core';
import {
  StringWithHighlightsPart,
  stringWithHighlightsFromMatch,
  Match,
} from '@app/lib/fuzzy_matcher';
import {OsqueryTableSpec} from './osquery_table_specs';


/** An item containing table info to display in the query helper menu */
@Component({
  selector: 'table-info-item',
  templateUrl: './table_info_item.ng.html',
  styleUrls: ['./table_info_item.scss'],
})
export class TableInfoItem {
  @Input()
  tableSpec?: OsqueryTableSpec;

  @Input()
  matchMap?: Map<string, Match>;

  get docsLinkToTable(): string {
    const tableName = this.tableSpec?.name;
    return `https://osquery.io/schema/4.5.1/#${tableName}`;
  }

  convertToHighlightedParts(
      subject: string,
  ): ReadonlyArray<StringWithHighlightsPart> {
    const matchResult = this.matchMap?.get(subject);

    if (matchResult) {
      const stringWithHighlights = stringWithHighlightsFromMatch(matchResult);
      return stringWithHighlights.parts;
    } else {
      return [
        {
          value: subject,
          highlight: false,
        }
      ];
    }
  }

  trackByIndex(index: number, _element: unknown): number {
    return index;
  }
}
