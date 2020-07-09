import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {Client} from '@app/lib/models/client';
import {ClientSearchFacade} from '@app/store/client_search_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {ClientSearch} from './client_search';
import {ClientSearchModule} from './module';
import {formatDate} from '@angular/common';
import {RelativeTimestampPipe} from '../timestamp/relative_timestamp_pipe';




initTestEnvironment();

function htmlCollectionToList(c: HTMLCollection): Element[] {
  const result: Element[] = [];
  for (let i = 0; i < c.length; ++i) {
    const item = c.item(i);
    if (item) {
      result.push(item);
    }
  }

  return result;
}

describe('ClientSearch Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientSearchFacade;

  beforeEach(async(() => {
    paramsSubject = new Subject();

    TestBed
      .configureTestingModule({
        imports: [
          NoopAnimationsModule,  // This makes test faster and more stable.
          ApiModule,
          ClientSearchModule,
          RouterTestingModule,
        ],
        providers: [{
          provide: ActivatedRoute,
          useValue: {
            paramMap: paramsSubject,
          },
        }],

      })
      .compileComponents();

    facade = TestBed.inject(ClientSearchFacade);
  }));

  it('triggers a new search on route change', () => {
    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    const searchClientsSpy = spyOn(facade, 'searchClients');
    paramsSubject.next(new Map([
      ['query', 'foo'],
    ]));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('foo');
  });

  it('displays a list of clients on clients change', () => {
    const subject = new Subject<Client[]>();
    Object.defineProperty(facade, 'clients$', {
      get() {
        return subject.asObservable();
      }
    });

    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    subject.next([
      {
        clientId: 'C.1234',
        fleetspeakEnabled: true,
        knowledgeBase: {
          fqdn: 'foo.unknown',
        },
        lastSeenAt: new Date(1571789996678),
        labels: [],
      },
      {
        clientId: 'C.5678',
        fleetspeakEnabled: true,
        knowledgeBase: {
          fqdn: 'bar.unknown',
        },
        labels: [],
      },
    ]);
    fixture.detectChanges();

    // Using nativeElement here instead of queryAll, since queryAll does
    // not go into child components DOM (in this case we're interested in
    // what's inside MatTable).
    const de: HTMLElement = fixture.debugElement.nativeElement;
    const rows = de.getElementsByTagName('tr');
    // First row is the header, two others are data.
    expect(rows.length).toBe(3);
    // Check the first data row.
    expect(htmlCollectionToList(rows[1].getElementsByTagName('td'))
      .map((e: Element) => (e as HTMLElement).innerText))
      .toEqual(['C.1234', 'foo.unknown', '2019-10-23 00:19:56 UTC']);
    // Check the second data row.
    expect(htmlCollectionToList(rows[2].getElementsByTagName('td'))
      .map((e: Element) => (e as HTMLElement).innerText))
      .toEqual(['C.5678', 'bar.unknown', 'Unknown']);
  });
});
