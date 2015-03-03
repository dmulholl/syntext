
// Resize the #content div so it fills the available vertical screen space.
$(function() {
    var header = $("#header").outerHeight();
    var footer = $("#footer").outerHeight();
    var chrome = $("#content").outerHeight() - $("#content").height();

    function resizeContent() {
        $("#content").css(
            'minHeight',
            $(window).height() - header - footer - chrome
        );
    }

    $(window).resize(resizeContent);
    resizeContent();
});
