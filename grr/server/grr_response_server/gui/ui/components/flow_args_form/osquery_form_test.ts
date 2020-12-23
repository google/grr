import {waitForAsync, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {By} from '@angular/platform-browser';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatChipListHarness} from '@angular/material/chips/testing';

import {initTestEnvironment} from '@app/testing';
import {OsqueryForm} from './osquery_form';
import {OsqueryArgs} from '@app/lib/api/api_interfaces';
import {OsqueryQueryHelperModule} from './osquery_query_helper/module';
import {CodeEditorModule} from '../code_editor/module';

initTestEnvironment();

describe('OsqueryForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            OsqueryQueryHelperModule,
            CodeEditorModule,
            MatIconModule,
            MatButtonModule,
            MatDialogModule,
            MatCheckboxModule,
            MatChipsModule,
            ReactiveFormsModule,
            MatFormFieldModule,
            MatInputModule,
            MatIconModule,
          ],
        })
        .compileComponents();
  }));

  function constructFixture(defaultFlowArgs: OsqueryArgs = {}) {
    const fixture = TestBed.createComponent(OsqueryForm);
    fixture.componentInstance.defaultFlowArgs = defaultFlowArgs;
    fixture.detectChanges();
    return fixture;
  };

  it('should display a code-editor,', () => {
    const fixture = constructFixture();

    const codeEditor = fixture.debugElement.query(By.css('code-editor'));
    expect(codeEditor).toBeTruthy();

    const browseSpecsButton = fixture.debugElement.query(
        By.css('.browse-tables-button'));
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display a browse tables button,', () => {
    const fixture = constructFixture();

    const browseSpecsButton = fixture.debugElement.query(
        By.css('.browse-tables-button'));
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display button for file collection settings and expand on click ',
      async () => {
        const fixture = constructFixture();
        const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

        const expandButtonHarness = await harnessLoader.getHarness(
            MatButtonHarness.with({text: /Show file collection settings.*/}),
        );
        await expandButtonHarness.click();

        const fileCollectionContainer =
            fixture.debugElement.query(By.css('.collection-container'));
        expect(fileCollectionContainer).toBeTruthy();
      });

  it('should display button for low-level settings and expand on click ',
      async () => {
        const fixture = constructFixture();
        const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

        const expandButtonHarness = await harnessLoader.getHarness(
            MatButtonHarness.with({text: /Show low-level settings.*/}),
        );
        await expandButtonHarness.click();

        const lowLevelSettingsContainer =
            fixture.debugElement.query(By.css('.settings-container'));
        expect(lowLevelSettingsContainer).toBeTruthy();
      });

  it('should have low-level and collection settings collapsed initially',
      () => {
        const fixture = constructFixture();

        const lowLevelSettingsContainer =
            fixture.debugElement.query(By.css('.settings-container'));
        const collectionContainer =
            fixture.debugElement.query(By.css('.collection-container'));

        expect(lowLevelSettingsContainer).toBeFalsy();

        expect(collectionContainer).toBeFalsy();
      });
  it('should have collection settings expanded when default flow args contain collection columns,',
      () => {
        const fixture = constructFixture({
          fileCollectionColumns: ['some collumn to collect files from'],
        });

        const collectionContainer =
            fixture.debugElement.query(By.css('.collection-container'));
        expect(collectionContainer).toBeTruthy();
      });

  it('updates the file collection form when a value is added',
      async () => {
        const fixture = constructFixture();
        const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

        // Here we expand the file collection settings just like the user would
        // do. At the moment of writing this, it is not strictly needed, since
        // the harnesses would find the elements even if it is collapsed.
        const expandButtonHarness = await harnessLoader.getHarness(
            MatButtonHarness.with({text: /Show file collection settings.*/}),
        );
        await expandButtonHarness.click();

        const collectionListHarness = await harnessLoader.getHarness(
            MatChipListHarness);

        const inputHarness = await collectionListHarness.getInput();
        await inputHarness.setValue('column1');
        await inputHarness.blur(); // The value is submitted on blur

        const chips = await collectionListHarness.getChips();
        const valuesInForm =
            fixture.componentInstance.form.get('fileCollectionColumns')?.value;

        expect(chips.length).toBe(1);
        expect(valuesInForm).toEqual(['column1'])
      });

  it('updates the file collection form when a value is removed',
      async () => {
        const fixture = constructFixture();
        const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

        // Here we expand the file collection settings just like the user would
        // do. At the moment of writing this, it is not strictly needed, since
        // the harnesses would find the elements even if it is collapsed.
        const expandButtonHarness = await harnessLoader.getHarness(
            MatButtonHarness.with({text: /Show file collection settings.*/}),
        );
        await expandButtonHarness.click();

        const collectionListHarness = await harnessLoader.getHarness(
            MatChipListHarness);

        const inputHarness = await collectionListHarness.getInput();
        await inputHarness.setValue('column1');
        await inputHarness.blur(); // The value is submitted on blur

        const chips = await collectionListHarness.getChips();
        expect(chips.length).toBe(1);

        await chips[0].remove();
        const chipsAfterRemoval = await collectionListHarness.getChips();
        const valuesInFormAfterRemoval =
            fixture.componentInstance.form.get('fileCollectionColumns')?.value;

        expect(chipsAfterRemoval.length).toBe(0);
        expect(valuesInFormAfterRemoval.length).toBe(0);
      });
});
