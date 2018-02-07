'use strict';

goog.provide('grrUi.core');
goog.provide('grrUi.core.coreModule');

goog.require('grrUi.core.aff4ObjectRepresentationDirective');  // USE: Aff4ObjectRepresentationDirective
goog.require('grrUi.core.apiItemsProviderDirective');  // USE: ApiItemsProviderDirective
goog.require('grrUi.core.apiService');                 // USE: ApiService
goog.require('grrUi.core.basenameFilter');             // USE: BasenameFilter
goog.require('grrUi.core.bindKeyDirective');           // USE: BindKeyDirective
goog.require('grrUi.core.bytesToHexFilter');           // USE: BytesToHexFilter
goog.require('grrUi.core.canaryOnlyDirective');  // USE: CanaryOnlyDirective, NonCanaryOnlyDirective
goog.require('grrUi.core.clockDirective');               // USE: ClockDirective
goog.require('grrUi.core.confirmationDialogDirective');  // USE: ConfirmationDialogDirective
goog.require('grrUi.core.dialogService');                // USE: DialogService
goog.require('grrUi.core.disableIfNoTraitDirective');  // USE: DisableIfNoTraitDirective
goog.require('grrUi.core.downloadCollectionAsDirective');  // USE: DownloadCollectionAsDirective
goog.require('grrUi.core.downloadCollectionFilesDirective');  // USE: DownloadCollectionFilesDirective
goog.require('grrUi.core.encodeUriComponentFilter');  // USE: EncodeUriComponentFilter
goog.require('grrUi.core.firebaseService');           // USE: FirebaseService
goog.require('grrUi.core.forceRefreshDirective');  // USE: ForceRefreshDirective
goog.require('grrUi.core.globalNotificationsDirective');  // USE: GlobalNotificationsDirective
goog.require('grrUi.core.hexNumberFilter');         // USE: HexNumberFilter
goog.require('grrUi.core.infiniteTableDirective');  // USE: InfiniteTableDirective
goog.require('grrUi.core.loadingIndicatorDirective');  // USE: LoadingIndicatorDirective
goog.require('grrUi.core.loadingIndicatorService');  // USE: LoadingIndicatorService
goog.require('grrUi.core.memoryItemsProviderDirective');  // USE: MemoryItemsProviderDirective
goog.require('grrUi.core.onScrollIntoViewDirective');  // USE: OnScrollIntoViewDirective
goog.require('grrUi.core.pagedFilteredTableDirective');  // USE: PagedFilteredTableDirective, TableBottomDirective, TableTopDirective
goog.require('grrUi.core.periodicRefreshDirective');  // USE: PeriodicRefreshDirective
goog.require('grrUi.core.reflectionService');         // USE: ReflectionService
goog.require('grrUi.core.resultsCollectionDirective');  // USE: ResultsCollectionDirective
goog.require('grrUi.core.searchBoxDirective');  // USE: SearchBoxDirective
goog.require('grrUi.core.serverErrorButtonDirective');  // USE: ServerErrorButtonDirective
goog.require('grrUi.core.serverErrorDialogDirective');  // USE: ServerErrorDialogDirective
goog.require('grrUi.core.serverErrorInterceptorFactory');  // USE: ServerErrorInterceptorFactory
goog.require('grrUi.core.serverErrorPreviewDirective');  // USE: ServerErrorPreviewDirective
goog.require('grrUi.core.splitterDirective');  // USE: SplitterDirective, SplitterPaneDirective
goog.require('grrUi.core.timeService');               // USE: TimeService
goog.require('grrUi.core.timeSinceFilter');           // USE: TimeSinceFilter
goog.require('grrUi.core.timestampFilter');           // USE: TimestampFilter
goog.require('grrUi.core.versionDropdownDirective');  // USE: VersionDropdownDirective
goog.require('grrUi.core.wizardFormDirective');      // USE: WizardFormDirective
goog.require('grrUi.core.wizardFormPageDirective');  // USE: WizardFormPageDirective


/**
 * Angular module for core GRR UI components.
 */
grrUi.core.coreModule = angular.module('grrUi.core', ['ngCookies',
                                                  'ui.bootstrap']);


grrUi.core.coreModule.directive(
    grrUi.core.aff4ObjectRepresentationDirective.Aff4ObjectRepresentationDirective.directive_name,
    grrUi.core.aff4ObjectRepresentationDirective.Aff4ObjectRepresentationDirective);
grrUi.core.coreModule.directive(
    grrUi.core.apiItemsProviderDirective.
        ApiItemsProviderDirective.directive_name,
    grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective);
grrUi.core.coreModule.directive(
    grrUi.core.bindKeyDirective.BindKeyDirective.directive_name,
    grrUi.core.bindKeyDirective.BindKeyDirective);
grrUi.core.coreModule.directive(
    grrUi.core.versionDropdownDirective.VersionDropdownDirective.directive_name,
    grrUi.core.versionDropdownDirective.VersionDropdownDirective);
grrUi.core.coreModule.directive(
    grrUi.core.forceRefreshDirective.ForceRefreshDirective.directive_name,
    grrUi.core.forceRefreshDirective.ForceRefreshDirective);
grrUi.core.coreModule.directive(
    grrUi.core.loadingIndicatorDirective.LoadingIndicatorDirective.directive_name,
    grrUi.core.loadingIndicatorDirective.LoadingIndicatorDirective);
grrUi.core.coreModule.directive(
    grrUi.core.onScrollIntoViewDirective.OnScrollIntoViewDirective
        .directive_name,
    grrUi.core.onScrollIntoViewDirective.OnScrollIntoViewDirective);
grrUi.core.coreModule.directive(
    grrUi.core.memoryItemsProviderDirective.
        MemoryItemsProviderDirective.directive_name,
    grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective);
grrUi.core.coreModule.directive(
    grrUi.core.pagedFilteredTableDirective.
        PagedFilteredTableDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective);
grrUi.core.coreModule.directive(
    grrUi.core.pagedFilteredTableDirective.TableTopDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.TableTopDirective);
grrUi.core.coreModule.directive(
    grrUi.core.pagedFilteredTableDirective.TableBottomDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.TableBottomDirective);
grrUi.core.coreModule.directive(
    grrUi.core.periodicRefreshDirective.PeriodicRefreshDirective.directive_name,
    grrUi.core.periodicRefreshDirective.PeriodicRefreshDirective);
grrUi.core.coreModule.directive(
    grrUi.core.infiniteTableDirective.InfiniteTableDirective.directive_name,
    grrUi.core.infiniteTableDirective.InfiniteTableDirective);
grrUi.core.coreModule.directive(
    grrUi.core.resultsCollectionDirective.ResultsCollectionDirective
        .directive_name,
    grrUi.core.resultsCollectionDirective.ResultsCollectionDirective);
grrUi.core.coreModule.directive(
    grrUi.core.splitterDirective.SplitterDirective.directive_name,
    grrUi.core.splitterDirective.SplitterDirective);
grrUi.core.coreModule.directive(
    grrUi.core.splitterDirective.SplitterPaneDirective.directive_name,
    grrUi.core.splitterDirective.SplitterPaneDirective);
grrUi.core.coreModule.directive(
    grrUi.core.clockDirective.ClockDirective.directive_name,
    grrUi.core.clockDirective.ClockDirective);
grrUi.core.coreModule.directive(
    grrUi.core.downloadCollectionAsDirective
        .DownloadCollectionAsDirective.directive_name,
    grrUi.core.downloadCollectionAsDirective
        .DownloadCollectionAsDirective);
grrUi.core.coreModule.directive(
    grrUi.core.downloadCollectionFilesDirective
        .DownloadCollectionFilesDirective.directive_name,
    grrUi.core.downloadCollectionFilesDirective
        .DownloadCollectionFilesDirective);
grrUi.core.coreModule.directive(
    grrUi.core.wizardFormDirective.WizardFormDirective.directive_name,
    grrUi.core.wizardFormDirective.WizardFormDirective);
grrUi.core.coreModule.directive(
    grrUi.core.wizardFormPageDirective.WizardFormPageDirective.directive_name,
    grrUi.core.wizardFormPageDirective.WizardFormPageDirective);
grrUi.core.coreModule.directive(
    grrUi.core.confirmationDialogDirective.ConfirmationDialogDirective.directive_name,
    grrUi.core.confirmationDialogDirective.ConfirmationDialogDirective);
grrUi.core.coreModule.directive(
    grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitDirective.directive_name,
    grrUi.core.disableIfNoTraitDirective.DisableIfNoTraitDirective);

grrUi.core.coreModule.directive(
    grrUi.core.canaryOnlyDirective.CanaryOnlyDirective.directive_name,
    grrUi.core.canaryOnlyDirective.CanaryOnlyDirective);
grrUi.core.coreModule.directive(
    grrUi.core.canaryOnlyDirective.NonCanaryOnlyDirective.directive_name,
    grrUi.core.canaryOnlyDirective.NonCanaryOnlyDirective);

grrUi.core.coreModule.directive(
    grrUi.core.searchBoxDirective.SearchBoxDirective.directive_name,
    grrUi.core.searchBoxDirective.SearchBoxDirective);
grrUi.core.coreModule.directive(
    grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.directive_name,
    grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective);
grrUi.core.coreModule.directive(
    grrUi.core.serverErrorDialogDirective.ServerErrorDialogDirective.directive_name,
    grrUi.core.serverErrorDialogDirective.ServerErrorDialogDirective);
grrUi.core.coreModule.directive(
    grrUi.core.serverErrorPreviewDirective.ServerErrorPreviewDirective.directive_name,
    grrUi.core.serverErrorPreviewDirective.ServerErrorPreviewDirective);
grrUi.core.coreModule.directive(
    grrUi.core.globalNotificationsDirective.GlobalNotificationsDirective.directive_name,
    grrUi.core.globalNotificationsDirective.GlobalNotificationsDirective);

grrUi.core.coreModule.service(
    grrUi.core.apiService.ApiService.service_name,
    grrUi.core.apiService.ApiService);
grrUi.core.coreModule.service(
    grrUi.core.firebaseService.FirebaseService.service_name,
    grrUi.core.firebaseService.FirebaseService);
grrUi.core.coreModule.service(
    grrUi.core.reflectionService.ReflectionService.service_name,
    grrUi.core.reflectionService.ReflectionService);
grrUi.core.coreModule.service(
    grrUi.core.timeService.TimeService.service_name,
    grrUi.core.timeService.TimeService);
grrUi.core.coreModule.service(
    grrUi.core.dialogService.DialogService.service_name,
    grrUi.core.dialogService.DialogService);
grrUi.core.coreModule.service(
    grrUi.core.loadingIndicatorService.LoadingIndicatorService.service_name,
    grrUi.core.loadingIndicatorService.LoadingIndicatorService);


grrUi.core.coreModule.filter(grrUi.core.basenameFilter.BasenameFilter.filter_name,
                         grrUi.core.basenameFilter.BasenameFilter);
grrUi.core.coreModule.filter(grrUi.core.bytesToHexFilter.BytesToHexFilter.filter_name,
                         grrUi.core.bytesToHexFilter.BytesToHexFilter);
grrUi.core.coreModule.filter(
    grrUi.core.encodeUriComponentFilter.EncodeUriComponentFilter.filter_name,
    grrUi.core.encodeUriComponentFilter.EncodeUriComponentFilter);
grrUi.core.coreModule.filter(grrUi.core.hexNumberFilter.HexNumberFilter.filter_name,
                         grrUi.core.hexNumberFilter.HexNumberFilter);
grrUi.core.coreModule.filter(grrUi.core.timeSinceFilter.TimeSinceFilter.filter_name,
                         grrUi.core.timeSinceFilter.TimeSinceFilter);
grrUi.core.coreModule.filter(grrUi.core.timestampFilter.TimestampFilter.filter_name,
                         grrUi.core.timestampFilter.TimestampFilter);

grrUi.core.coreModule.factory(
    grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory.factory_name,
    grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory);


grrUi.core.coreModule.config(function($httpProvider){
    $httpProvider.interceptors.push(
        grrUi.core.serverErrorInterceptorFactory.ServerErrorInterceptorFactory.factory_name
    );
});
