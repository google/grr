
module("attributes");

test( "attrFn test", function() {
	expect( 4 );

	( jQuery._definePropertyBroken ? expectNoWarning : expectWarning )( "attrFn", function() {
		ok( !!jQuery.attrFn, "attrFn present" );
		equal( jQuery.attrFn.quack, undefined, "can read values from attrFn" );
		jQuery.attrFn.quack = true;
		equal( jQuery.attrFn.quack, true, "can assign new values to attrFn" );
	});
});

test( "warn if changing an input or button", function() {
	expect( 4 );

	var $div = jQuery("<div />"),
		$input = jQuery("<input type=text />"),
		$button = jQuery("<button type=button>click</button>");

	expectNoWarning( "input type change", function() {
		$div.appendTo("#qunit-fixture").attr( "type", "fancy" );
	});

	expectNoWarning( "$(html, props) signature", function() {
		jQuery( "<button>", { type: "button" } );
	});

	expectWarning( "input type change", function() {
		try {
			$input.appendTo("#qunit-fixture").attr( "type", "checkbox" );
		} catch ( e ) { }
	});

	expectWarning( "button type change", function() {
		try {
			$button.appendTo("#qunit-fixture").attr( "type", "submit" );
		} catch ( e ) { }
	});
});

test( "attrHooks[\"value\"]", function() {
	expect( 20 );

	expectWarning( "input.attr('value')", 0, function() {
		var input = jQuery("<input/>");
		equal( input.attr("value"), "", "input.attr('value') returns initially empty property." );
		input[0].value = "foo";
		equal( input.attr("value"), "foo", "input.attr('value') returns property." );
	});

	expectWarning( "textarea.attr('value')", 1, function() {
		equal( jQuery("#area1").attr("value"), "foobar", "textarea.attr('value') returns property." );
	});

	expectWarning( "input.attr('value', val)", 0, function() {
		var el = jQuery("#text1").attr( "value", "foo" );
		equal( el[0].getAttributeNode("value").value, "foo", "input.attr('value', val) sets attribute." );
		equal( el[0].value, "foo", "input.attr('value', val) sets property." );
	});

	expectWarning( "textarea.attr('value', val)", 1, function() {
		var el = jQuery("#area1").attr( "value", "foo" );
		equal( el[0].value, "foo", "textarea.attr('value', val) sets property." );
	});

	expectWarning( "select.attr('value', val)", 1, function() {
		var el = jQuery("#select1").attr( "value", "2" );
		equal( el[0].value, "2", "select.attr('value', val) sets property." );
	});

	expectWarning( "button.attr(...)", 0, function() {
		var button = jQuery("#button"),
			majorMinorPatch = jQuery.fn.jquery.split(".");

		// Respect the jQuery 1.9.0+ behavior changes
		if ( majorMinorPatch[0] > 1 || ( majorMinorPatch[0] === "1" && majorMinorPatch[1] >= 9 ) ) {
			equal( button.attr("value"), undefined, "button.attr('value') returns attribute." );
			equal( button.attr( "value", "foo" ).attr("value"), "foo", "button.attr('value', val) sets attribute." );
		} else {
			ok( !button.attr("value"), "button.attr('value') is falsy." );
			ok( true, "Can't assert consistency of button.attr('value', val) on jQuery<1.9.0." );
		}
		equal( button.attr( "value", "bar" ).html(), "Button", "button.attr('value') doesn't affect contents" );
	});

	expectWarning( "div.attr(...)", 2, function() {
		var div = jQuery("#foo");
		equal( div.attr("value"), undefined, "div.attr('value') returns attribute." );
		equal( div.attr( "value", "bar" ).attr("value"), "bar", "div.attr('value', val) sets attribute." );
		equal( div[0].value, "bar", "div.attr('value', val) sets property." );
	});
});

test( "boolean attributes (boolHook)", function() {
	expect( 42 );

	expectWarning( ".attr(checked)", 1, function() {
		jQuery("#check2").prop( "checked", true ).prop( "checked", false ).attr( "checked", true );
		equal( document.getElementById("check2").checked, true, "Set checked attribute" );
		equal( jQuery("#check2").prop("checked"), true, "Set checked attribute" );
		equal( jQuery("#check2").attr("checked"), "checked", "Set checked attribute" );
		jQuery("#check2").attr( "checked", false );
		equal( document.getElementById("check2").checked, false, "Set checked attribute" );
		equal( jQuery("#check2").prop("checked"), false, "Set checked attribute" );
		equal( jQuery("#check2").attr("checked"), undefined, "Set checked attribute" );
	});
	expectWarning( ".attr(selected)", 1, function() {
		jQuery("#option3d").prop( "selected", true ).prop( "selected", false ).attr( "selected", true );
		equal( document.getElementById("option3d").selected, true, "Set selected attribute" );
		equal( jQuery("#option3d").prop("selected"), true, "Set selected attribute" );
		equal( jQuery("#option3d").attr("selected"), "selected", "Set selected attribute" );
		jQuery("#option3d").attr( "selected", false );
		equal( document.getElementById("option3d").selected, false, "Set selected attribute" );
		equal( jQuery("#option3d").prop("selected"), false, "Set selected attribute" );
		equal( jQuery("#option3d").attr("selected"), undefined, "Set selected attribute" );
	});
	expectWarning( ".attr(readonly)", 0, function() {
		jQuery("#text1").attr( "readonly", true );
		equal( document.getElementById("text1").readOnly, true, "Set readonly attribute" );
		equal( jQuery("#text1").prop("readOnly"), true, "Set readonly attribute" );
		equal( jQuery("#text1").attr("readonly"), "readonly", "Set readonly attribute" );
		jQuery("#text1").attr( "readonly", false );
		equal( document.getElementById("text1").readOnly, false, "Set readonly attribute" );
		equal( jQuery("#text1").prop("readOnly"), false, "Set readonly attribute" );
		equal( jQuery("#text1").attr("readonly"), undefined, "Set readonly attribute" );
	});

	jQuery("#check2").prop( "checked", true );
	equal( document.getElementById("check2").checked, true, "Set checked attribute" );
	equal( jQuery("#check2").prop("checked"), true, "Set checked attribute" );
	equal( jQuery("#check2").attr("checked"), "checked", "Set checked attribute" );
	jQuery("#check2").prop( "checked", false );
	equal( document.getElementById("check2").checked, false, "Set checked attribute" );
	equal( jQuery("#check2").prop("checked"), false, "Set checked attribute" );
	equal( jQuery("#check2").attr("checked"), undefined, "Set checked attribute" );

	jQuery("#check2").attr("checked", "checked");
	equal( document.getElementById("check2").checked, true, "Set checked attribute with 'checked'" );
	equal( jQuery("#check2").prop("checked"), true, "Set checked attribute" );
	equal( jQuery("#check2").attr("checked"), "checked", "Set checked attribute" );


	var $radios = jQuery("#checkedtest").find("input[type='radio']");
	$radios.eq( 1 ).click();
	equal( $radios.eq( 1 ).prop("checked"), true, "Second radio was checked when clicked" );
	equal( $radios.attr("checked"), $radios[ 0 ].checked ? "checked" : undefined, "Known booleans do not fall back to attribute presence (#10278)" );

	jQuery("#text1").prop( "readOnly", true );
	equal( document.getElementById("text1").readOnly, true, "Set readonly attribute" );
	equal( jQuery("#text1").prop("readOnly"), true, "Set readonly attribute" );
	equal( jQuery("#text1").attr("readonly"), "readonly", "Set readonly attribute" );
	jQuery("#text1").prop( "readOnly", false );
	equal( document.getElementById("text1").readOnly, false, "Set readonly attribute" );
	equal( jQuery("#text1").prop("readOnly"), false, "Set readonly attribute" );
	equal( jQuery("#text1").attr("readonly"), undefined, "Set readonly attribute" );


	// HTML5 boolean attributes
	expectWarning( ".attr(HTML5)", 0, function() {
		var $text = jQuery("#text1").attr({
			"autofocus": true,
			"required": true
		});
		equal( $text.attr("autofocus"), "autofocus", "Set boolean attributes to the same name" );
		equal( $text.attr( "autofocus", false ).attr("autofocus"), undefined, "Setting autofocus attribute to false removes it" );
		equal( $text.attr("required"), "required", "Set boolean attributes to the same name" );
	});
});
