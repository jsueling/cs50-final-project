// Find every input on the page
var portfolios = document.querySelectorAll("input");
// Find the button
var button = document.getElementById("button");

// For each input add eventlistener that, on click, runs the function checked()
for(var i = 0; i < portfolios.length; i++) {
    portfolios[i].addEventListener("click", checked);
}

// This function looks for a single checked input on the page and enables the button if true
// and disables when there are no checked inputs
// Trying to stop the user from submitting a blank form
// The user can check and then uncheck inputs

// It's inefficient to iterate over all inputs in the form once we find 1 checked input.
// So we can break the for loop
// https://www.w3schools.com/js/js_break.asp
function checked() {

    var counter = 0;

    for(var i = 0; i < portfolios.length; i++) {
        
        if (portfolios[i].checked) {
            counter++;                
        }
        if (counter > 0) { break; }
    }
    
    if (counter > 0) {
        button.disabled = false;
    } else {
        button.disabled = true;
    }
};