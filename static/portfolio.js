// Find every bar on the page
var bars = document.querySelectorAll(".bar");

// For each bar add eventlistener that changes current window location to the value of the attribute data-link
// which will link to /portfolio/<portfolio_name>/share/<unique_id>
for(var i = 0; i < bars.length; i++) {
    bars[i].addEventListener("click", function(){
        window.location.href = this.getAttribute("data-link");
    });
}