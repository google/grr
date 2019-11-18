import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Router} from '@angular/router';



/**
 * Provides the top-most component for the GRR UI home page.
 */
@Component({
  templateUrl: './home.ng.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home {
  constructor(private readonly router: Router) {}

  /**
   * Event handler for the search box. Gets triggered when a user initiates
   * the client search.
   */
  onQuerySubmitted(query: string) {
    this.router.navigate(['v2/client-search', query]);
  }
}
