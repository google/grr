import {
    ChangeDetectionStrategy,
    Component,
    ViewChild,
    ElementRef,
    AfterViewInit,
    ViewEncapsulation,
    Input,
    forwardRef,
    OnDestroy,
    HostBinding,
} from '@angular/core';
import {NG_VALUE_ACCESSOR, ControlValueAccessor, NgControl} from '@angular/forms';
import {MatFormFieldControl} from '@angular/material/form-field';
import {Subject} from 'rxjs';
import {FocusMonitor} from '@angular/cdk/a11y';
import {takeUntil} from 'rxjs/operators';
import {isNonNull} from '@app/lib/preconditions';

import CodeMirror from 'codemirror';
// importing sql-hint is needed for SQL syntax highlighting
import 'codemirror/addon/hint/sql-hint.js';
// importing show-hint is needed for the autocomplete pop-up
import 'codemirror/addon/hint/show-hint.js';

type OnChangeFn = (textValue: string) => void;

/** The core functionality of the code editor */
class CodeEditorCore implements AfterViewInit, ControlValueAccessor {
  @ViewChild('editorTarget')
  private readonly editorTarget!: ElementRef;
  protected editor?: CodeMirror.Editor;

  private latestOverwrite = '';
  @Input()
  set editorValue(newValue: string) {
    // The editor is initialized in ngAfterViewInit, and will be undefined
    // before that, including when @Input() arguments are set.
    // See ngAfterViewInit.
    this.editor?.setValue(newValue);
    this.latestOverwrite = newValue;
  }
  get editorValue() {
    return this.editor?.getValue() ?? '';
  }
  protected readonly editorValueChanges$ = new Subject<string>();

  // ControlValueAccessor functionality
  private announceValueChanged: OnChangeFn = () => { };
  writeValue(value: string): void {
    this.editorValue = value;
  }
  registerOnChange(fn: OnChangeFn): void {
    this.announceValueChanged = fn;
  }
  registerOnTouched(): void { }

  ngAfterViewInit(): void {
    this.initializeEditor();

    // We have to re-set the editor value so that it contains the initial text
    // because input arguments are bound prior to ngAfterViewInit, when editor
    // was still undefined.
    this.editorValue = this.latestOverwrite;
  }

  private initializeEditor(): void {
    this.editor = CodeMirror.fromTextArea(this.editorTarget.nativeElement, {
      value: '',
      mode: 'text/x-sqlite',
      theme: 'neo',
      extraKeys: {'Ctrl-Space': 'autocomplete'},
      lineNumbers: true,
      lineWrapping: true,
    });

    this.editor.on('change', () => {
      this.announceValueChanged(this.editorValue);
      this.editorValueChanges$.next(this.editorValue);
    });
  }
}

/**
 * Displays a code editor.
 * It can be used as an Angular form field, and it can be put inside
 * <mat-form-field></mat-form-field> tags.
 *
 * @see {@link CodeEditorCore}
 */
@Component({
  selector: 'code-editor',
  templateUrl: './code_editor.ng.html',
  styleUrls: ['./code_editor.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CodeEditor),
      multi: true,
    },
    {
      provide: MatFormFieldControl,
      useExisting: CodeEditor,
      multi: true,
    }
  ],
})
export class CodeEditor extends CodeEditorCore
    implements MatFormFieldControl<string>, OnDestroy {
  private static uniqueNumber = 0;

  private readonly unsubscribe$ = new Subject<void>();

  readonly controlType = 'code-editor';

  private _id?: string;
  @HostBinding()
  get id(): string {
    if (!this._id) {
      this._id = `${this.controlType}-${CodeEditor.uniqueNumber}`;
      CodeEditor.uniqueNumber += 1;
    }

    return this._id;
  }

  get value(): string {
    return this.editorValue;
  }
  set value(newValue: string) {
    this.editorValue = newValue;
  }

  get empty(): boolean {
    return this.editorValue === '';
  }

  readonly stateChanges = new Subject<void>();
  focused = false;

  // not implemented
  shouldLabelFloat = true;

  // not implemented
  required = false;

  // not implemented
  disabled = false;

  // not implemented
  placeholder = '';

  // not implemented
  ngControl: NgControl | null = null;

  // not implemented
  errorState = false;

  /**
   * Whether the code editor input will be focused when the enclosing
   * mat-form-field container is clicked
   */
  @Input()
  focusOnContainerClick = true;
  onContainerClick(event: MouseEvent): void {
    if (this.focusOnContainerClick) {
      this.editor?.focus();
    }
  }

  // not implemented
  setDescribedByIds(ids: string[]): void { }

  constructor(
      private focusMonitor: FocusMonitor,
      private rootElement: ElementRef<HTMLElement>,
  ) {
    super();
    focusMonitor.monitor(rootElement.nativeElement, true).subscribe(
        focused => {
          this.focused = isNonNull(focused);
          this.stateChanges.next();
        });

    this.editorValueChanges$.pipe(
        takeUntil(this.unsubscribe$)
      ).subscribe(() => {
        this.stateChanges.next();
      });
  }

  ngOnDestroy(): void {
    this.focusMonitor.stopMonitoring(this.rootElement.nativeElement);

    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
