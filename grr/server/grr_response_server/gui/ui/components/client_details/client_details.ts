import {ChangeDetectionStrategy, Component, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {Client} from '@app/lib/models/client';
import {diff} from 'deep-diff';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';

interface ClientVersion {
  client: Client;
  changes: string[];
}

/**
 * Component displaying the details for a single Client.
 */
@Component({
  templateUrl: './client_details.ng.html',
  styleUrls: ['./client_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientDetails implements OnInit, OnDestroy {
  // Not static & private because is referenced in the template
  readonly INITIAL_NUM_USERS_SHOWN = 1;
  readonly INITIAL_NUM_INTERFACES_SHOWN = 3;
  readonly INITIAL_NUM_VOLUMES_SHOWN = 2;

  private readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter((id): id is string => id !== null));

  readonly client$ = this.clientPageFacade.selectedClient$;
  readonly clientVersions$ = this.clientPageFacade.selectedClientVersions$.pipe(
      map(snapshots => snapshots.reverse()),
      map(this.getClientVersions),
  );

  currentNumUsersShown = this.INITIAL_NUM_USERS_SHOWN;
  currentNumInterfacesShown = this.INITIAL_NUM_INTERFACES_SHOWN;
  currentNumVolumesShown = this.INITIAL_NUM_VOLUMES_SHOWN;

  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });
  }

  getAccordionButtonState(
      totalNumElements: number, currentMaxNumElementsShown: number,
      initialMaxNumElementsShown: number): string {

    if (totalNumElements > currentMaxNumElementsShown) {
      return 'show-more';
    } else if (totalNumElements <= initialMaxNumElementsShown) {
      return 'no-button';
    }
    return 'show-less';
  }

  static getChange(current: Client, old?: Client): string[]|undefined {
    if (old === undefined) {
      return ['Client created'];
    }

    let difference = diff(old, current);

    // Client's snapshot `age` property doesn't count as a real change
    difference = difference?.filter(
        (diffElem) =>
            diffElem.path !== undefined && diffElem.path[0] !== 'age');

    // If no difference found between snapshots
    if (difference === undefined || difference.length === 0) {
      return undefined;
    }

    return ['Client updated']
  }

  /**
   * Converts an array of snapshots into an array of client versions also
   * containing the changes between versions.
   * @param clientSnapshots an array of chronologically reverse ordered client
   *     snapshots
   */
  getClientVersions(clientSnapshots: Client[]): ClientVersion[] {
    let clientChanges: ClientVersion[] = [];

    for (let i = 0; i < clientSnapshots.length; i++) {
      const clientChange =
          ClientDetails.getChange(clientSnapshots[i], clientSnapshots[i + 1]);
      if (clientChange !== undefined) {
        clientChanges.push({
          client: clientSnapshots[i],
          changes: clientChange,
        });
      }
    }

    return clientChanges;
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
