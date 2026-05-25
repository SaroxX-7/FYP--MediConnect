(function () {
    'use strict';

    const patterns = {
        email: /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
    };

    function injectStyles() {
        if (document.getElementById('auth-validation-styles')) return;

        const style = document.createElement('style');
        style.id = 'auth-validation-styles';
        style.textContent = `
            .form-group.form-focus {
                margin-bottom: 1.35rem;
            }

            .auth-field-error {
                color: #dc2626;
                font-size: 0.78rem;
                font-weight: 600;
                margin: 7px 0 0 14px;
                display: block;
                line-height: 1.3;
            }

            .form-focus .form-control.is-invalid {
                border: 2px solid #ef4444 !important;
                box-shadow: none !important;
                background: #ffffff !important;
            }

            .form-focus .form-control.is-valid {
                border: 2px solid #10b981 !important;
                box-shadow: none !important;
                background: #ffffff !important;
            }

            .form-focus .form-control.is-invalid ~ .focus-label {
                color: #ef4444 !important;
                background: #ffffff !important;
            }

            .form-focus .form-control.is-valid ~ .focus-label {
                color: #10b981 !important;
                background: #ffffff !important;
            }

            .form-focus .form-control:focus.is-invalid {
                border-color: #ef4444 !important;
                box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.10) !important;
            }

            .form-focus .form-control:focus.is-valid {
                border-color: #10b981 !important;
                box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.10) !important;
            }
        `;
        document.head.appendChild(style);
    }

    function getFormGroup(input) {
        return input.closest('.form-group') || input.parentElement;
    }

    function clearError(input) {
        const group = getFormGroup(input);
        const oldError = group.querySelector('.auth-field-error');

        if (oldError) {
            oldError.remove();
        }

        input.classList.remove('is-invalid');
        input.removeAttribute('aria-invalid');
    }

    function showError(input, message) {
        const group = getFormGroup(input);

        clearError(input);

        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        input.setAttribute('aria-invalid', 'true');

        const error = document.createElement('small');
        error.className = 'auth-field-error';
        error.textContent = message;

        group.appendChild(error);
    }

    function markValid(input) {
        clearError(input);

        if (input.value.trim() !== '') {
            input.classList.add('is-valid');
        }
    }

    function validateEmail(input) {
        const value = input.value.trim();

        if (!value) {
            return 'Email address is required.';
        }

        if (!patterns.email.test(value)) {
            return 'Enter a valid email address.';
        }

        return '';
    }

    function validatePassword(input) {
        const value = input.value.trim();

        if (!value) {
            return 'Password is required.';
        }

        return '';
    }

    function runValidation(input, validator) {
        const message = validator(input);

        if (message) {
            showError(input, message);
            return false;
        }

        markValid(input);
        return true;
    }

    document.addEventListener('DOMContentLoaded', function () {
        injectStyles();

        const form = document.getElementById('loginForm');
        if (!form) return;

        const emailInput = form.querySelector('#email');
        const passwordInput = form.querySelector('#password');

        if (emailInput) {
            emailInput.addEventListener('blur', function () {
                runValidation(emailInput, validateEmail);
            });

            emailInput.addEventListener('input', function () {
                clearError(emailInput);
                emailInput.classList.remove('is-valid');
            });
        }

        if (passwordInput) {
            passwordInput.addEventListener('blur', function () {
                runValidation(passwordInput, validatePassword);
            });

            passwordInput.addEventListener('input', function () {
                clearError(passwordInput);
                passwordInput.classList.remove('is-valid');
            });
        }

        form.addEventListener('submit', function (event) {
            let isValid = true;

            if (emailInput) {
                isValid = runValidation(emailInput, validateEmail) && isValid;
            }

            if (passwordInput) {
                isValid = runValidation(passwordInput, validatePassword) && isValid;
            }

            if (!isValid) {
                event.preventDefault();

                const firstInvalid = form.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
        });
    });
})();