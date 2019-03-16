
var matched, browser,
	oldInit = jQuery.fn.init,
	oldFind = jQuery.find,
	oldParseJSON = jQuery.parseJSON,
	rspaceAngle = /^\s*</,
	rattrHashTest = /\[(\s*[-\w]+\s*)([~|^$*]?=)\s*([-\w#]*?#[-\w#]*)\s*\]/,
	rattrHashGlob = /\[(\s*[-\w]+\s*)([~|^$*]?=)\s*([-\w#]*?#[-\w#]*)\s*\]/g,
	// Note: XSS check is done below after string is trimmed
	rquickExpr = /^([^<]*)(<[\w\W]+>)([^>]*)$/;

// $(html) "looks like html" rule change
jQuery.fn.init = function( selector, context, rootjQuery ) {
	var match, ret;

	if ( selector && typeof selector === "string" ) {
		if ( !jQuery.isPlainObject( context ) &&
				(match = rquickExpr.exec( jQuery.trim( selector ) )) && match[ 0 ] ) {

			// This is an HTML string according to the "old" rules; is it still?
			if ( !rspaceAngle.test( selector ) ) {
				migrateWarn("$(html) HTML strings must start with '<' character");
			}
			if ( match[ 3 ] ) {
				migrateWarn("$(html) HTML text after last tag is ignored");
			}

			// Consistently reject any HTML-like string starting with a hash (gh-9521)
			// Note that this may break jQuery 1.6.x code that otherwise would work.
			if ( match[ 0 ].charAt( 0 ) === "#" ) {
				migrateWarn("HTML string cannot start with a '#' character");
				jQuery.error("JQMIGRATE: Invalid selector string (XSS)");
			}

			// Now process using loose rules; let pre-1.8 play too
			// Is this a jQuery context? parseHTML expects a DOM element (#178)
			if ( context && context.context && context.context.nodeType ) {
				context = context.context;
			}

			if ( jQuery.parseHTML ) {
				return oldInit.call( this,
						jQuery.parseHTML( match[ 2 ], context && context.ownerDocument ||
							context || document, true ), context, rootjQuery );
			}
		}
	}

	ret = oldInit.apply( this, arguments );

	// Fill in selector and context properties so .live() works
	if ( selector && selector.selector !== undefined ) {
		// A jQuery object, copy its properties
		ret.selector = selector.selector;
		ret.context = selector.context;

	} else {
		ret.selector = typeof selector === "string" ? selector : "";
		if ( selector ) {
			ret.context = selector.nodeType? selector : context || document;
		}
	}

	return ret;
};
jQuery.fn.init.prototype = jQuery.fn;

jQuery.find = function( selector ) {
	var args = Array.prototype.slice.call( arguments );

	// Support: PhantomJS 1.x
	// String#match fails to match when used with a //g RegExp, only on some strings
	if ( typeof selector === "string" && rattrHashTest.test( selector ) ) {

		// The nonstandard and undocumented unquoted-hash was removed in jQuery 1.12.0
		// First see if qS thinks it's a valid selector, if so avoid a false positive
		try {
			document.querySelector( selector );
		} catch ( err1 ) {

			// Didn't *look* valid to qSA, warn and try quoting what we think is the value
			selector = selector.replace( rattrHashGlob, function( _, attr, op, value ) {
				return "[" + attr + op + "\"" + value + "\"]";
			} );

			// If the regexp *may* have created an invalid selector, don't update it
			// Note that there may be false alarms if selector uses jQuery extensions
			try {
				document.querySelector( selector );
				migrateWarn( "Attribute selector with '#' must be quoted: " + args[ 0 ] );
				args[ 0 ] = selector;
			} catch ( err2 ) {
				migrateWarn( "Attribute selector with '#' was not fixed: " + args[ 0 ] );
			}
		}
	}

	return oldFind.apply( this, args );
};

// Copy properties attached to original jQuery.find method (e.g. .attr, .isXML)
var findProp;
for ( findProp in oldFind ) {
	if ( Object.prototype.hasOwnProperty.call( oldFind, findProp ) ) {
		jQuery.find[ findProp ] = oldFind[ findProp ];
	}
}

// Let $.parseJSON(falsy_value) return null
jQuery.parseJSON = function( json ) {
	if ( !json ) {
		migrateWarn("jQuery.parseJSON requires a valid JSON string");
		return null;
	}
	return oldParseJSON.apply( this, arguments );
};

jQuery.uaMatch = function( ua ) {
	ua = ua.toLowerCase();

	var match = /(chrome)[ \/]([\w.]+)/.exec( ua ) ||
		/(webkit)[ \/]([\w.]+)/.exec( ua ) ||
		/(opera)(?:.*version|)[ \/]([\w.]+)/.exec( ua ) ||
		/(msie) ([\w.]+)/.exec( ua ) ||
		ua.indexOf("compatible") < 0 && /(mozilla)(?:.*? rv:([\w.]+)|)/.exec( ua ) ||
		[];

	return {
		browser: match[ 1 ] || "",
		version: match[ 2 ] || "0"
	};
};

// Don't clobber any existing jQuery.browser in case it's different
if ( !jQuery.browser ) {
	matched = jQuery.uaMatch( navigator.userAgent );
	browser = {};

	if ( matched.browser ) {
		browser[ matched.browser ] = true;
		browser.version = matched.version;
	}

	// Chrome is Webkit, but Webkit is also Safari.
	if ( browser.chrome ) {
		browser.webkit = true;
	} else if ( browser.webkit ) {
		browser.safari = true;
	}

	jQuery.browser = browser;
}

// Warn if the code tries to get jQuery.browser
migrateWarnProp( jQuery, "browser", jQuery.browser, "jQuery.browser is deprecated" );

// jQuery.boxModel deprecated in 1.3, jQuery.support.boxModel deprecated in 1.7
jQuery.boxModel = jQuery.support.boxModel = (document.compatMode === "CSS1Compat");
migrateWarnProp( jQuery, "boxModel", jQuery.boxModel, "jQuery.boxModel is deprecated" );
migrateWarnProp( jQuery.support, "boxModel", jQuery.support.boxModel, "jQuery.support.boxModel is deprecated" );

jQuery.sub = function() {
	function jQuerySub( selector, context ) {
		return new jQuerySub.fn.init( selector, context );
	}
	jQuery.extend( true, jQuerySub, this );
	jQuerySub.superclass = this;
	jQuerySub.fn = jQuerySub.prototype = this();
	jQuerySub.fn.constructor = jQuerySub;
	jQuerySub.sub = this.sub;
	jQuerySub.fn.init = function init( selector, context ) {
		var instance = jQuery.fn.init.call( this, selector, context, rootjQuerySub );
		return instance instanceof jQuerySub ?
			instance :
			jQuerySub( instance );
	};
	jQuerySub.fn.init.prototype = jQuerySub.fn;
	var rootjQuerySub = jQuerySub(document);
	migrateWarn( "jQuery.sub() is deprecated" );
	return jQuerySub;
};

// The number of elements contained in the matched element set
jQuery.fn.size = function() {
	migrateWarn( "jQuery.fn.size() is deprecated; use the .length property" );
	return this.length;
};
