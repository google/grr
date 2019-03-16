
module( "traversing" );

test( ".andSelf", function(){
    expect( 1 );

    expectWarning( "andSelf", function() {
        jQuery( "<div id='outer'><div id='inner'></div></div>").find( ".inner").andSelf();
    });
});
