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

import {initTestEnvironment} from '@app/testing';
import {OsqueryForm} from './osquery_form';
import {OsqueryFlowArgs} from '@app/lib/api/api_interfaces';
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

  function constructFixture(defaultFlowArgs: OsqueryFlowArgs = {}) {
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

  it('should have collection settings expanded when default flow args contain collection columns,',
      () => {
        const fixture = constructFixture({
          fileCollectColumns: ['some collumn to collect files from'],
        });

        const lowLevelSettingsContainer =
            fixture.debugElement.query(By.css('.collection-container'));
        expect(lowLevelSettingsContainer).toBeTruthy();
      });
});
