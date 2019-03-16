
module("data");

test( "basic .data() sanity check", function() {
	expect( 4 );

	var $foo = jQuery("#foo");

	equal( $foo.data("x"), undefined, "no data initially" );
	$foo.data( "x", 42 );
	equal( $foo.data("x"), 42, "set a numeric value" );
	$foo.data( "x", function(){ alert("whoops"); });
	equal( typeof $foo.data("x"), "function", "set a function value" );
	$foo.removeData("x");
	equal( $foo.data("x"), undefined, "data was removed" );
});

test( "jQuery.fn.data('events')", function() {
	expect( 6 );

	var $foo = jQuery("#foo");

	expectNoWarning( "$.data('events')", function() {
		equal( $foo.data("events"), undefined, "no events initially" );
		$foo.data("events", 42);
		equal( $foo.data("events"), 42, "got our own defined data" );
		$foo.removeData("events");
		equal( $foo.data("events"), undefined, "no events again" );
	});
	expectWarning( "$.data('events')", function() {
		$foo.bind( "click", jQuery.noop );
		equal( typeof $foo.data("events"), "object", "got undocumented events object" );
		$foo.unbind( "click", jQuery.noop );
	});
});
