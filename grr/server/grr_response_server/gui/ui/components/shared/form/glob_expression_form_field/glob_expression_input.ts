import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  forwardRef,
  Input,
  ViewChild,
} from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
  UntypedFormControl,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatOptionModule} from '@angular/material/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {MatInputModule} from '@angular/material/input';
import {BehaviorSubject, combineLatest} from 'rxjs';
import {map, startWith} from 'rxjs/operators';

import {
  getKnowledgeBaseExpressionExamples,
  KnowledgeBaseExample,
  type Client,
} from '../../../../lib/models/client';
import {GlobExpressionExplanation} from './glob_expression_explanation';

type OnChangeFn = (value: string) => void;
type OnTouchedFn = () => void;

function getSelectedGlobExpressionPart(text: string, cursor: number) {
  const textBeforeCursor = text.slice(0, cursor);
  const fragments = textBeforeCursor.split('%%');
  if (fragments.length === 0 || fragments.length % 2 === 1) {
    return null;
  } else {
    return fragments[fragments.length - 1];
  }
}

/** mat-form-field for GlobExpression inputs. */
@Component({
  selector: 'glob-expression-input',
  templateUrl: './glob_expression_input.ng.html',
  styleUrls: ['./glob_expression_input.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    GlobExpressionExplanation,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatOptionModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => GlobExpressionInput),
      multi: true,
    },
  ],
})
export class GlobExpressionInput
  implements ControlValueAccessor, AfterViewInit
{
  onChange: OnChangeFn = () => {};

  private onTouched: OnTouchedFn = () => {};

  readonly client$ = new BehaviorSubject<Client | null>(null);

  readonly formControl = new UntypedFormControl('');

  @Input()
  set client(client: Client | null) {
    this.client$.next(client);
  }

  get client() {
    return this.client$.value;
  }

  @ViewChild('input') input!: ElementRef<HTMLInputElement>;

  private readonly knowledgeBaseExamples$ = this.client$.pipe(
    map((client) =>
      client ? getKnowledgeBaseExpressionExamples(client.knowledgeBase) : [],
    ),
  );

  readonly filteredKnowledgeBaseExamples$ = combineLatest([
    this.knowledgeBaseExamples$,
    this.formControl.valueChanges.pipe<string>(startWith('')),
  ]).pipe(
    map(([examples, query]) => {
      const cursorPosition =
        this.input?.nativeElement.selectionStart ?? query.length;
      const fragment = getSelectedGlobExpressionPart(
        query,
        cursorPosition,
      )?.toLocaleLowerCase();

      if (fragment === undefined) {
        return [];
      }

      const queryBefore = query.slice(0, cursorPosition - fragment.length - 2);
      const queryAfter = query.slice(cursorPosition);

      return examples
        .filter((e) => e.key.includes(fragment))
        .map((e) => ({...e, value: queryBefore + e.key + queryAfter}));
    }),
  );

  ngAfterViewInit() {
    this.input.nativeElement.addEventListener('input', () => {
      this.onChange(this.input.nativeElement.value);
    });
    this.input.nativeElement.addEventListener('blur', () => {
      this.onTouched();
    });
  }

  writeValue(obj: string | undefined | null) {
    this.formControl.setValue(obj ?? '');
    // Allow early calls to writeValue before views have been initialized.
    if (this.input?.nativeElement) {
      this.input.nativeElement.value = obj ?? '';
    }
  }

  registerOnChange(fn: OnChangeFn) {
    this.onChange = fn;
  }

  registerOnTouched(fn: OnTouchedFn) {
    this.onTouched = fn;
  }

  trackExample(index: number, example: KnowledgeBaseExample) {
    return example.key;
  }
}
