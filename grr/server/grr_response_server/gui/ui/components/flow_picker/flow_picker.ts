import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {FlowDescriptor} from '@app/lib/models/flow';
import {combineLatest, fromEvent, Subject} from 'rxjs';
import {filter, map, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';

import {FlowFacade} from '../../store/flow_facade';

function groupByCategory(entries: FlowEntry[]):
    ReadonlyMap<string, ReadonlyArray<FlowEntry>> {
  const map = new Map<string, FlowEntry[]>();
  entries.forEach(entry => {
    const arr = map.get(entry.category);
    if (arr === undefined) {
      map.set(entry.category, [entry]);
    } else {
      arr.push(entry);
    }
  });
  return map;
}

interface FlowEntry extends FlowDescriptor {
  highlighted: boolean;
}

/**
 * Returns a function that converts a FlowDescriptor to a FlowEntry,
 * adding a `highlighted` attribute that is true iff the FlowDescriptor should
 * be highlighted based on the user input `highlightQuery`.
 */
function highlightWith(highlightQuery: string):
    ((fd: FlowDescriptor) => FlowEntry) {
  highlightQuery = highlightQuery.toLowerCase();
  return fd => ({
           ...fd,
           highlighted: fd.friendlyName.toLowerCase().includes(highlightQuery),
         });
}

/**
 * Component that displays available Flows.
 */
@Component({
  selector: 'flow-picker',
  templateUrl: './flow_picker.ng.html',
  styleUrls: ['./flow_picker.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowPicker implements OnInit, OnDestroy, AfterViewInit {
  private readonly unsubscribe$ = new Subject<void>();
  readonly textInput = new FormControl('');
  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  readonly textInput$ = this.textInput.valueChanges.pipe(
      startWith(''),
  );

  readonly flowDescriptors$ = this.flowFacade.flowDescriptors$.pipe(
      map(fds => Array.from(fds.values())),
  );

  readonly flowEntries$ =
      combineLatest([this.flowDescriptors$, this.textInput$])
          .pipe(
              map(([fds, textInput]) => fds.map(highlightWith(textInput))),
              map(groupByCategory),
          );

  readonly selectedFlow$ = this.flowFacade.selectedFlow$;

  constructor(
      private readonly flowFacade: FlowFacade,
  ) {}

  ngOnInit() {
    this.flowFacade.listFlowDescriptors();
  }

  ngAfterViewInit() {
    fromEvent(this.form.nativeElement, 'submit')
        .pipe(
            takeUntil(this.unsubscribe$),
            withLatestFrom(this.flowEntries$),
            map(([_, entries]) => Array.from(entries.values()).flat()),
            // Only select a flow on enter press if there is exactly 1
            // highlighted flow that matches the user input.
            map((entries: FlowEntry[]) => entries.filter(f => f.highlighted)),
            filter(entries => entries.length === 1),
            )
        .subscribe(([fd]) => {
          this.selectFlow(fd.name);
        });
  }

  unselectFlow() {
    this.flowFacade.unselectFlow();
  }

  selectFlow(name: string) {
    this.flowFacade.selectFlow(name);
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
