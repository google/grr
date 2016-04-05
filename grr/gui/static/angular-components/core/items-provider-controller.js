'use strict';

goog.provide('grrUi.core.itemsProviderController.Items');
goog.provide('grrUi.core.itemsProviderController.ItemsProviderController');


goog.scope(function() {


/** @typedef {!Object|{
 *             offset:?number,
 *             totalCount:?number,
 *             items:Array<?>
 *           }}
 */
grrUi.core.itemsProviderController.Items;



/**
 * Interface for items providers used by directives displaying collections
 * (i.e. InfiniteTableDirective and PagedFilteredTableDirective).
 *
 * @interface
 * @export
 */
grrUi.core.itemsProviderController.ItemsProviderController = function() {};
var ItemsProviderController =
    grrUi.core.itemsProviderController.ItemsProviderController;


/**
 * Fetches specified number of collection items starting from a given offset.
 *
 * @param {number} offset Items will be fetched from collection starting at
 *     this offset.
 * @param {number} count Number of items to be fetched.
 * @param {boolean=} opt_withTotalCount if true, total number of elements in
 *     the collection will be returned along with fetched items.
 * @return {!angular.$q.Promise} Fetched items promise. Resolves to
 *     grrUi.core.itemsProviderController.Items. If opt_withTotalCount
 *     was set to true, resulting object will have a totalCount attribute
 *     containing total number of items in the collection on the server.
 */
ItemsProviderController.prototype.fetchItems = goog.abstractMethod;


/**
 * Fetches specified number of collection items filtered by a given token
 * starting from a given offset.
 *
 * @param {string} filter Token to be used for filtering.
 * @param {number} offset Number of items to skip in the resulting set.
 * @param {number} count Maximum number of items to be returned.
 * @return {!angular.$q.Promise} Fetched items promise. Resolves to
 *     grrUi.core.itemsProviderController.Items.
 */
ItemsProviderController.prototype.fetchFilteredItems = goog.abstractMethod;

});  // goog.scope
