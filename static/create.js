// This script tests if browser supports input="date" and returns the compatible html
// https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date#javascript
// IE11 input="date" falls back to "text"

// define variables
var nativePicker = document.querySelector('.nativeDatePicker');
var fallbackPicker = document.querySelector('.fallbackDatePicker');

// hide fallback initially
fallbackPicker.style.display = 'none';

// test whether a new date input falls back to a text input or not
var test = document.createElement('input');

// Sends 'Invalid Input' to console if error
try {
    test.type = 'date';
} catch (e) {
    console.log(e.description);
}

// if the test falls back to text
if(test.type === 'text') {
    // hide the native picker and show the fallback
    // .style.display = 'inline'
    nativePicker.style.display = 'none';
    fallbackPicker.style.display = 'inline';
}

// https://stackoverflow.com/questions/49863189/disable-weekends-on-html-5-input-type-date
// Takes the date this.value from the input, converts it into a day of the 
// week using Coordinated Universal time 0 through 6 where 1 is Monday
// If the day from input is Sat or Sun (0 or 6)
// Display a confirmation message, ask the user if he wants to continue
// if true (pressed OK) do nothing, the page continues as normal
// if false (pressed cancel) preventDefault to override the submit action
// set the date back to null

const form = document.getElementById("form");
const date1 = document.getElementById("date1");

form.addEventListener("submit", function(e){
    let day = new Date(date1.value).getUTCDay();
    if([6,0].includes(day)){
        if(!confirm("The date selected is a weekend where exchanges are normally closed, Press OK if you want to continue.")){
            e.preventDefault();
            date1.value = '';
        }
    }
});