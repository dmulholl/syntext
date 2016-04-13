// Resize the #main div so it fills the available vertical screen space.
$(function() {
    var header_height = $("#head").outerHeight();
    var footer_height = $("#foot").outerHeight();

    function resizeContent() {
        $("#main").css(
            'minHeight',
            $(window).height() - header_height - footer_height
        );
    }

    $(window).resize(resizeContent);
    resizeContent();
});
