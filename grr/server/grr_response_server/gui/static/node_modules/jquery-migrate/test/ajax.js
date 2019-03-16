
module("ajax");

// Can't run this in PhantomJS because it's a local file
if ( window.location.protocol !== "file:" ) {

	test( "jQuery.ajax() with empty JSON string", function() {
		expect( 2 );

		stop();
		jQuery.migrateReset();
		jQuery.ajax({
			url: "data/empty.json",
			dataType: "json",
			cache: false,
			success: function( data ) {
				equal( data, null, "empty string converted to null" );
				// We only generate 1 warning but jQuery < 1.11 uses .unload() internally
				ok( jQuery.migrateWarnings.length > 0, "warned" );
			},
			error: function( xhr, msg ) {
				ok( false, "error: "+ msg );
			},
			complete: function() {
				start();
			}
		});
	});

	test( "jQuery.ajax() with 'null' JSON string", function() {
		expect( 2 );

		stop();
		jQuery.migrateReset();
		jQuery.ajax({
			url: "data/null.json",
			dataType: "json",
			cache: false,
			success: function( data ) {
				equal( data, null, "'null' converted to null" );
				equal( jQuery.migrateWarnings.length, 0, "did not warn" );
			},
			error: function( xhr, msg ) {
				ok( false, "error: "+ msg );
			},
			complete: function() {
				start();
			}
		});
	});

	test( "jQuery.ajax() with simple JSON string", function() {
		expect( 2 );

		stop();
		jQuery.migrateReset();
		jQuery.ajax({
			url: "data/simple.json",
			dataType: "json",
			cache: false,
			success: function( data ) {
				equal( data.gibson, 42, "right answer" );
				equal( jQuery.migrateWarnings.length, 0, "did not warn" );
			},
			error: function( xhr, msg ) {
				ok( false, "error: "+ msg );
			},
			complete: function() {
				start();
			}
		});
	});
}