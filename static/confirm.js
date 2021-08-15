// Confirm message to prevent accidental deletion
var button = document.querySelector("#deletebutton");

button.addEventListener("click", function(e) {
    if(!confirm("Are you sure?")) {
        e.preventDefault();
    }
});