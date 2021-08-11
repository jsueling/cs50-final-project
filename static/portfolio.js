// Link to the corresponding element

// For all bars on the page
// Add onclick to redirect

// Find every bar on the page
var bars = document.querySelectorAll(".bar");

// For each bar add eventlistener that changes current window location to the value of the attribute data-link
for(var i = 0; i < bars.length; i++) {
    bars[i].addEventListener("click", function(){
        window.location.href = this.getAttribute("data-link");
    });
}