(function trackActiveElement() {

    document.lastActiveElement = undefined;

    document.addEventListener("focusout", function (focusEvent) {
        var target = focusEvent.target;
        document.lastActiveElement = target
    })

}())
