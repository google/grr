import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {filter, map, takeUntil, withLatestFrom} from 'rxjs/operators';

import {FlowState} from '../../lib/models/flow';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {UserGlobalStore} from '../../store/user_global_store';


/**
 * Component displaying the details and actions for a single Client.
 */
@Component({
  templateUrl: './client_page.ng.html',
  styleUrls: ['./client_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly hasAccess$ = this.clientPageGlobalStore.hasAccess$;


  readonly interrogateInProgress$ =
      this.clientPageGlobalStore.flowListEntries$.pipe(map(
          data => data.flows?.find(
              f => f.name === 'Interrogate' && f.state === FlowState.RUNNING)));

  // If GetGrrUser() would expose the email, we could show an online
  // notification in progress if any user selects to notify the email of the
  // current user. Since the email is not exposed, we show the flow as in
  // progress if the current user started it.
  readonly onlineNotificationInProgress$ =
      this.clientPageGlobalStore.flowListEntries$.pipe(
          withLatestFrom(this.userGlobalStore.currentUser$),
          map(([data, user]) => data.flows?.find(
                  f => f.name === 'OnlineNotification' &&
                      f.creator === user.name &&
                      f.state === FlowState.RUNNING)));



  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageGlobalStore: ClientPageGlobalStore,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
      private readonly title: Title,
  ) {
    this.selectedClientGlobalStore.selectClientId(
        this.route.paramMap.pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('id')),
            filter(isNonNull),
            ),
    );

    this.selectedClientGlobalStore.clientId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(isNonNull),
            )
        .subscribe(id => {
          this.clientPageGlobalStore.selectClient(id);
        });

    this.clientPageGlobalStore.selectedClient$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(client => {
          if (client) {
            const fqdn = client.knowledgeBase.fqdn;
            const info =
                fqdn ? `${fqdn} (${client.clientId})` : client.clientId;
            this.title.setTitle(`GRR | ${info}`);
          } else {
            this.title.setTitle('GRR');
          }
        });
  }

  triggerOnlineNotification() {
    this.clientPageGlobalStore.startFlowConfiguration('OnlineNotification');
  }

  triggerInterrogate() {
    this.clientPageGlobalStore.startFlowConfiguration('Interrogate');
  }
}
