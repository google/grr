'use strict';

goog.module('grrUi.client.virtualFileSystem.virtualFileSystem');
goog.module.declareLegacyNamespace();

const {BreadcrumbsDirective} = goog.require('grrUi.client.virtualFileSystem.breadcrumbsDirective');
const {EncodingsDropdownDirective} = goog.require('grrUi.client.virtualFileSystem.encodingsDropdownDirective');
const {FileContextDirective} = goog.require('grrUi.client.virtualFileSystem.fileContextDirective');
const {FileDetailsDirective} = goog.require('grrUi.client.virtualFileSystem.fileDetailsDirective');
const {FileDownloadViewDirective} = goog.require('grrUi.client.virtualFileSystem.fileDownloadViewDirective');
const {FileHexViewDirective} = goog.require('grrUi.client.virtualFileSystem.fileHexViewDirective');
const {FileStatsViewDirective} = goog.require('grrUi.client.virtualFileSystem.fileStatsViewDirective');
const {FileTableDirective} = goog.require('grrUi.client.virtualFileSystem.fileTableDirective');
const {FileTextViewDirective} = goog.require('grrUi.client.virtualFileSystem.fileTextViewDirective');
const {FileTimelineDirective} = goog.require('grrUi.client.virtualFileSystem.fileTimelineDirective');
const {FileTreeDirective} = goog.require('grrUi.client.virtualFileSystem.fileTreeDirective');
const {FileViewDirective} = goog.require('grrUi.client.virtualFileSystem.fileViewDirective');
const {RWeOwnedButtonDirective} = goog.require('grrUi.client.virtualFileSystem.rWeOwnedButtonDirective');
const {RecursiveListButtonDirective} = goog.require('grrUi.client.virtualFileSystem.recursiveListButtonDirective');
const {VfsFilesArchiveButtonDirective} = goog.require('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {semanticModule} = goog.require('grrUi.semantic.semantic');



/**
 * Angular module for clients-related UI.
 */
exports.virtualFileSystemModule = angular.module(
    'grrUi.client.virtualFileSystem', [coreModule.name, semanticModule.name]);

exports.virtualFileSystemModule.directive(
    BreadcrumbsDirective.directive_name, BreadcrumbsDirective);
exports.virtualFileSystemModule.directive(
    EncodingsDropdownDirective.directive_name, EncodingsDropdownDirective);
exports.virtualFileSystemModule.directive(
    FileContextDirective.directive_name, FileContextDirective);
exports.virtualFileSystemModule.directive(
    FileDetailsDirective.directive_name, FileDetailsDirective);
exports.virtualFileSystemModule.directive(
    FileDownloadViewDirective.directive_name, FileDownloadViewDirective);
exports.virtualFileSystemModule.directive(
    FileHexViewDirective.directive_name, FileHexViewDirective);
exports.virtualFileSystemModule.directive(
    FileStatsViewDirective.directive_name, FileStatsViewDirective);
exports.virtualFileSystemModule.directive(
    FileTableDirective.directive_name, FileTableDirective);
exports.virtualFileSystemModule.directive(
    FileTimelineDirective.directive_name, FileTimelineDirective);
exports.virtualFileSystemModule.directive(
    FileTextViewDirective.directive_name, FileTextViewDirective);
exports.virtualFileSystemModule.directive(
    FileTreeDirective.directive_name, FileTreeDirective);
exports.virtualFileSystemModule.directive(
    FileViewDirective.directive_name, FileViewDirective);
exports.virtualFileSystemModule.directive(
    RecursiveListButtonDirective.directive_name, RecursiveListButtonDirective);
exports.virtualFileSystemModule.directive(
    VfsFilesArchiveButtonDirective.directive_name,
    VfsFilesArchiveButtonDirective);
exports.virtualFileSystemModule.directive(
    RWeOwnedButtonDirective.directive_name, RWeOwnedButtonDirective);
