
module("core");

test( "jQuery.migrateVersion", function( assert ) {
	assert.expect( 1 );

	assert.ok( /^\d+\.\d+\.[\w\-]+/.test( jQuery.migrateVersion ), "Version property" );
});

test( "jQuery(html, props)", function() {
	expect( 3 );

	var $el = jQuery( "<input/>", { name: "name", val: "value", size: 42 } );

	equal( $el.attr("name"), "name", "Name attribute" );
	equal( $el.attr("size"), jQuery.isEmptyObject(jQuery.attrFn) ? undefined : "42", "Size attribute" );
	equal( $el.val(), "value", "Call setter method" );
});

test( "jQuery(html) loose rules", function() {
	expect( 33 );

	var w,
		nowarns = {
			"simple tag": "<div />",
			"single tag with properties": "<input type=text name=easy />",
			"embedded newlines": "<div>very\nspacey\n like\n<div> text </div></div>",
			"embedded hash": "<p>love potion <strong bgcolor='#bad'>#9</strong></p>",
			"complex html": "<div id='good'><p id='guy'> hello !</p></div>",
			"leading space": "  <div />",
			"leading newline": "\n<div />",
			"lots of space/newline": "  <em>  spaces \n and \n newlines </em> \n "
		},
		warns = {
			"leading text": "don't<div>try this</div>",
			"trailing text": "<div>try this</div>junk",
			"both text": "don't<div>try this</div>either"
		},
		generate = function( html ) {
			return function() {
				var el = jQuery( html );

				equal( el.length, 1, html + " succeeded" );
				equal( el.parent().length, 0, html + " generated new content" );
			};
		};

	for ( w in nowarns ) {
		expectNoWarning( w, generate( nowarns[w] ) );
	}
	for ( w in warns ) {
		expectWarning( w, generate( warns[w] ) );
	}
});

// Selector quoting doesn't work in IE<8
if ( document.querySelector ) {

QUnit.test( "Attribute selectors with unquoted hashes", function( assert ) {
	expect( 33 );

	var markup = jQuery(
			"<div>" +
				"<div data-selector='a[href=#main]'></div>" +
				"<a href='space#junk'>test</a>" +
				"<link rel='good#stuff' />" +
				"<p class='space #junk'>" +
					"<a href='#some-anchor'>anchor2</a>" +
					"<input value='[strange*=#stuff]' />" +
					"<a href='#' data-id='#junk'>anchor</a>" +
				"</p>" +
			"</div>" ).appendTo( "#qunit-fixture" ),

		// No warning, no need to fix
		okays = [
			"a[href='#some-anchor']",
			"[data-id=\"#junk\"]",
			"div[data-selector='a[href=#main]']",
			"input[value~= '[strange*=#stuff]']"
		],

		// Fixable, and gives warning
		fixables = [
			"a[href=#]",
			".space a[href=#]",
			"a[href=#some-anchor]",
			"link[rel*=#stuff]",
			"p[class *= #junk]",
			"a[href=space#junk]"
		],

		// False positives that still work
		positives = [
			"div[data-selector='a[href=#main]']:first",
			"input[value= '[strange*=#stuff]']:eq(0)"
		],

		// Failures due to quotes and jQuery extensions combined
		failures = [
			"p[class ^= #junk]:first",
			"a[href=space#junk]:eq(1)"
		];

	expectNoWarning( "Perfectly cromulent selectors are unchanged", function() {
		jQuery.each( okays, function( _, okay ) {
			assert.equal( jQuery( okay, markup ).length, 1, okay );
			assert.equal( markup.find( okay ).length, 1, okay );
		} );
	} );

	expectWarning( "Values with unquoted hashes are quoted", fixables.length, function() {
		jQuery.each( fixables, function( _, fixable ) {
			assert.equal( jQuery( fixable, markup ).length, 1, fixable );
			assert.equal( markup.find( fixable ).length, 1, fixable );
		} );
	} );

	expectWarning( "False positives", positives.length, function() {
		jQuery.each( positives, function( _, positive ) {
			assert.equal( jQuery( positive, markup ).length, 1,  positive );
			assert.equal( markup.find( positive ).length, 1, positive );
		} );
	} );

	expectWarning( "Unfixable cases", failures.length, function() {
		jQuery.each( failures, function( _, failure ) {
			try {
				jQuery( failure, markup );
				assert.ok( true, "jQuery() may die, it didn't" );
			} catch ( err1 ) {
				assert.ok( true, "jQuery() may die, it did" );
			}
			try {
				markup.find( failure );
				assert.ok( true, ".find() may die, it didn't" );
			} catch ( err2 ) {
				assert.ok( true, ".find() may die, it did" );
			}
		} );
	} );

	// Ensure we don't process jQuery( x ) when x is a function
	expectNoWarning( "ready function with attribute selector", function() {
		try {
			jQuery( function() {
				if ( jQuery.thisIsNeverDefined ) {
					jQuery( "a[href=#junk]" );
				}
			} );
		} catch( e ) {}
	});
});

}

QUnit.test( "document.context defined (#178)", function( assert ) {
	assert.expect( 1 );

	var span = jQuery( "<span>hi</span>" ).appendTo( "#qunit-fixture" );
	try {
		document.context = "!!hosed!!";
		span.wrap( "<p></p>" );
		assert.ok( true, "document.context did not kill jQuery" );
	} catch ( err ) {
		assert.ok( false, "died while wrapping" );
	}

	// Can't delete this property because of oldIE
	document.context = null;
} );

test( "selector state", function() {
	expect( 18 );

	var test;

	test = jQuery( undefined );
	equal( test.selector, "", "Empty jQuery Selector" );
	equal( test.context, undefined, "Empty jQuery Context" );

	test = jQuery( document );
	equal( test.selector, "", "Document Selector" );
	equal( test.context, document, "Document Context" );

	test = jQuery( document.body );
	equal( test.selector, "", "Body Selector" );
	equal( test.context, document.body, "Body Context" );

	test = jQuery("#qunit-fixture");
	equal( test.selector, "#qunit-fixture", "#qunit-fixture Selector" );
	equal( test.context, document, "#qunit-fixture Context" );

	test = jQuery("#notfoundnono");
	equal( test.selector, "#notfoundnono", "#notfoundnono Selector" );
	equal( test.context, document, "#notfoundnono Context" );

	test = jQuery( "#qunit-fixture", document );
	equal( test.selector, "#qunit-fixture", "#qunit-fixture Selector" );
	equal( test.context, document, "#qunit-fixture Context" );

	test = jQuery( "#qunit-fixture", document.body );
	equal( test.selector, "#qunit-fixture", "#qunit-fixture Selector" );
	equal( test.context, document.body, "#qunit-fixture Context" );

	// Test cloning
	test = jQuery( test );
	equal( test.selector, "#qunit-fixture", "#qunit-fixture Selector" );
	equal( test.context, document.body, "#qunit-fixture Context" );

	test = jQuery( document.body ).find("#qunit-fixture");
	equal( test.selector, "#qunit-fixture", "#qunit-fixture find Selector" );
	equal( test.context, document.body, "#qunit-fixture find Context" );
});

test( "XSS injection", function() {
	expect( 10 );

	// IE6 doesn't throw exceptions, just skip it since the XSS is still stopped
	var expectThrow = navigator.userAgent.indexOf( "MSIE 6" ) < 0;

	// Bad HTML will throw on some supported versions
	expectWarning( "leading hash", function() {
		try {
			jQuery("#yeah<p>RIGHT</p>");
		} catch ( e ) {}
	});

	// Don't expect HTML if there's a leading hash char; this is
	// more strict than the 1.7 version but closes an XSS hole.

	expectWarning( "XSS via script tag", function() {
		var threw = false;
		window.XSS = false;
		try {
			jQuery( "#<script>window.XSS=true<" + "/script>" );
		} catch ( e ) {
			threw = true;
		}
		equal( threw, expectThrow, "Throw on leading-hash HTML (treated as selector)" );
		equal( window.XSS, false, "XSS" );
	});

	expectWarning( "XSS with hash and leading space", function() {
		var threw = false;
		window.XSS = false;
		try {
			jQuery( " \n#<script>window.XSS=true<" + "/script>" );
		} catch ( e ) {
			threw = true;
		}
		equal( threw, expectThrow, "Throw on leading-hash HTML and space (treated as selector)" );
		equal( window.XSS, false, "XSS" );
	});

	expectWarning( "XSS via onerror inline handler", function() {
		var threw = false;
		window.XSS = false;
		try {
			jQuery( "#<img src=haha onerror='window.XSS=true' />" );
		} catch ( e ) {
			threw = true;
		}
		equal( threw, expectThrow, "Throw on leading-hash HTML (treated as selector)" );
		stop();
		setTimeout(function() {
			equal( window.XSS, false, "XSS" );
			start();
		}, 1000);
	});
});

test( "jQuery( '<element>' ) usable on detached elements (#128)" , function() {
	expect( 1 );

	jQuery( "<a>" ).outerWidth();
	ok( true, "No crash when operating on detached elements with window" );
});

test( "jQuery.parseJSON() falsy values", function() {
	expect(6);

	expectNoWarning( "valid JSON", function() {
		jQuery.parseJSON("{\"a\":1}");
	});
	expectWarning( "actual null", function() {
		jQuery.parseJSON(null);
	});
	expectNoWarning( "string null", function() {
		jQuery.parseJSON("null");
	});
	expectWarning( "empty string", function() {
		jQuery.parseJSON("");
	});
	expectWarning( "Boolean false", function() {
		jQuery.parseJSON(false);
	});
	expectWarning( "undefined", function() {
		jQuery.parseJSON(undefined);
	});
});

test( "jQuery.browser", function() {
	expect( 3 );

	( jQuery._definePropertyBroken ? expectNoWarning : expectWarning )( "browser", function() {
		ok( jQuery.browser, "jQuery.browser present" );
		ok( jQuery.browser.version, "have a browser version" );
	});
});

test( "jQuery.boxModel and jQuery.support.boxModel", function() {
	expect( 3 );

	( jQuery._definePropertyBroken ? expectNoWarning : expectWarning )( "boxModel", 2, function() {
		equal( jQuery.boxModel, true, "jQuery.boxModel is true (not in Quirks)" );
		equal( jQuery.support.boxModel, true, "jQuery.support.boxModel is true (not in Quirks)" );
	});
});

test( "jQuery.sub() - Static Methods", function(){
	expect( 19 );

	var Subclass, SubSubclass;

	// Other warnings may be fired when props are copied
	expectWarning( "jQuery.sub", function() {
		Subclass = jQuery.sub();
	});

	Subclass.extend({
		"topLevelMethod": function() {return this.debug;},
		"debug": false,
		"config": {
			"locale": "en_US"
		},
		"setup": function(config) {
			this.extend(true, this["config"], config);
		}
	});
	Subclass.fn.extend({"subClassMethod": function() { return this;}});

	//Test Simple Subclass
	ok(Subclass["topLevelMethod"]() === false, "Subclass.topLevelMethod thought debug was true");
	ok(Subclass["config"]["locale"] === "en_US", Subclass["config"]["locale"] + " is wrong!");
	deepEqual(Subclass["config"]["test"], undefined, "Subclass.config.test is set incorrectly");
	equal(jQuery.ajax, Subclass.ajax, "The subclass failed to get all top level methods");

	//Create a SubSubclass
	SubSubclass = Subclass.sub();

	//Make Sure the SubSubclass inherited properly
	ok(SubSubclass["topLevelMethod"]() === false, "SubSubclass.topLevelMethod thought debug was true");
	ok(SubSubclass["config"]["locale"] === "en_US", SubSubclass["config"]["locale"] + " is wrong!");
	deepEqual(SubSubclass["config"]["test"], undefined, "SubSubclass.config.test is set incorrectly");
	equal(jQuery.ajax, SubSubclass.ajax, "The subsubclass failed to get all top level methods");

	//Modify The Subclass and test the Modifications
	SubSubclass.fn.extend({"subSubClassMethod": function() { return this;}});
	SubSubclass["setup"]({"locale": "es_MX", "test": "worked"});
	SubSubclass["debug"] = true;
	SubSubclass.ajax = function() {return false;};
	ok(SubSubclass["topLevelMethod"](), "SubSubclass.topLevelMethod thought debug was false");
	deepEqual(SubSubclass(document)["subClassMethod"], Subclass.fn["subClassMethod"], "Methods Differ!");
	ok(SubSubclass["config"]["locale"] === "es_MX", SubSubclass["config"]["locale"] + " is wrong!");
	ok(SubSubclass["config"]["test"] === "worked", "SubSubclass.config.test is set incorrectly");
	notEqual(jQuery.ajax, SubSubclass.ajax, "The subsubclass failed to get all top level methods");

	//This shows that the modifications to the SubSubClass did not bubble back up to it's superclass
	ok(Subclass["topLevelMethod"]() === false, "Subclass.topLevelMethod thought debug was true");
	ok(Subclass["config"]["locale"] === "en_US", Subclass["config"]["locale"] + " is wrong!");
	deepEqual(Subclass["config"]["test"], undefined, "Subclass.config.test is set incorrectly");
	deepEqual(Subclass(document)["subSubClassMethod"], undefined, "subSubClassMethod set incorrectly");
	equal(jQuery.ajax, Subclass.ajax, "The subclass failed to get all top level methods");
});

test( "jQuery.sub() - .fn Methods", function(){
	expect( 378 );

	var Subclass = jQuery.sub(),
		SubSubclass = Subclass.sub(),
		jQueryDocument = jQuery( document ),
		contexts = [ undefined, document, jQueryDocument ],
		selectors = [ "body", "html,body", "<div></div>" ],
		methodArguments = {
			"eq": 1 ,
			"add": document,
			"end": undefined,
			"has": undefined,
			"closest": "div",
			"filter": document,
			"find": "div"
		};

	jQueryDocument.toString = function() {
		return "jQueryDocument";
	};

	Subclass.fn.subMethod = function(){};
	SubSubclass.fn.subSubMethod = function(){};

	jQuery.each( contexts, function( i, context ) {
			jQuery.each( selectors, function( i, selector ) {
				jQuery.each( methodArguments, function( method, arg ){

				var description = "(\"" + selector + "\", " + context + ")." + method + "(" + (arg || "") + ")",
					$instance = jQuery( selector, context )[ method ]( arg ),
					$subInstance = Subclass( selector, context )[ method ]( arg ),
					$subSubInstance = SubSubclass( selector, context )[ method ]( arg );

				// jQuery
				strictEqual( $instance.subMethod, undefined,
					"jQuery" + description + " doesn't have Subclass methods" );
				strictEqual( $instance.subSubMethod, undefined,
					"jQuery" + description + " doesn't have SubSubclass methods" );

				// Subclass
				strictEqual( $subInstance.subMethod, Subclass.fn.subMethod,
					"Subclass" + description + " has Subclass methods" );
				strictEqual( $subInstance.subSubMethod, undefined,
					"Subclass" + description + " doesn't have SubSubclass methods" );

				// SubSubclass
				strictEqual( $subSubInstance.subMethod, Subclass.fn.subMethod,
					"SubSubclass" + description + " has Subclass methods" );
				strictEqual( $subSubInstance.subSubMethod, SubSubclass.fn.subSubMethod,
					"SubSubclass" + description + " has SubSubclass methods" );
			});
		});
	});
});

test( ".size", function(){
    expect( 1 );

    expectWarning( "size", function() {
        jQuery( "<div />" ).size();
    });
});
