import {AfterViewInit, ChangeDetectionStrategy, Component, ElementRef, OnDestroy, ViewChild} from '@angular/core';
import {FormControl} from '@angular/forms';
import {FlowDescriptor} from '@app/lib/models/flow';
import {combineLatest, fromEvent, Subject} from 'rxjs';
import {filter, map, startWith, takeUntil, withLatestFrom} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {FORMS} from '../flow_args_form/sub_forms';

// During early development of UI v2, we don't want to display all legacy flows.
// These flows have no form, so displaying them only clutters the UI for the
// user. Instead, only show flows that have a form implemented.
const FLOW_DESCRIPTORS_WITH_FORM = new Set(Object.keys(FORMS));

function flowDescriptorHasForm(fd: FlowDescriptor): boolean {
  return FLOW_DESCRIPTORS_WITH_FORM.has(fd.name);
}

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
export class FlowPicker implements OnDestroy, AfterViewInit {
  private readonly unsubscribe$ = new Subject<void>();

  readonly textInput = new FormControl('');
  @ViewChild('form') form!: ElementRef<HTMLFormElement>;

  private readonly textInput$ = this.textInput.valueChanges.pipe(
      startWith(''),
  );

  private readonly flowDescriptors$ = this.configFacade.flowDescriptors$.pipe(
      map(fds => Array.from(fds.values())),
      map(fds => fds.filter(flowDescriptorHasForm)),
  );

  readonly flowEntries$ =
      combineLatest([this.flowDescriptors$, this.textInput$])
          .pipe(
              map(([fds, textInput]) => fds.map(highlightWith(textInput))),
              map(groupByCategory),
          );

  readonly selectedFlow$ = this.clientPageFacade.selectedFlowDescriptor$;

  constructor(
      private readonly configFacade: ConfigFacade,
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

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
    this.clientPageFacade.stopFlowConfiguration();
  }

  selectFlow(name: string) {
    this.clientPageFacade.startFlowConfiguration(name);
  }

  trackFlowDescriptor(index: number, fd: FlowDescriptor) {
    return fd.name;
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
