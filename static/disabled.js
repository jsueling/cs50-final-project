// https://github.com/whatwg/html/issues/5312

// Double click or spam clicking a submit button on
// a form results in multiple POST requests.
// This is usually not what the user intends and its not good for the application.

// What this Javascript does:
// Find every form,
// For each form add eventlistener to submit action e.g. <button type="submit"
// On submit if the class contains is-submitting,
// prevent default action, stop propagation, return false
// else if not
// add class is-submitting

// In other words, allow the action of submit to happen once,
// and any more submits have no effect

document.querySelectorAll('form').forEach((form) => {
	form.addEventListener('submit', (e) => {
		if (form.classList.contains('is-submitting')) {
			e.preventDefault();
			e.stopPropagation();
			return false;	
		};

		form.classList.add('is-submitting');
	});
});