import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {Router} from '@angular/router';

import {isClientId} from '../../lib/models/client';

/**
 * Provides the top-most component for the GRR UI home page.
 */
@Component({
  templateUrl: './home.ng.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Home {
  constructor(
      private readonly router: Router,
      title: Title,
  ) {
    title.setTitle('GRR');
  }

  /**
   * Event handler for the search box. Gets triggered when a user initiates
   * the client search.
   */
  onQuerySubmitted(query: string) {
    if (isClientId(query)) {
      this.router.navigate(['/clients', query]);
    } else {
      this.router.navigate(['/clients'], {queryParams: {'q': query}});
    }
  }
}
