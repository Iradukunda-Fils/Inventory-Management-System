document.addEventListener('DOMContentLoaded', function() {
    // Form validation
    const forms = document.querySelectorAll('.auth-form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input');
        
        inputs.forEach(input => {
            // Add floating label effect
            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });
            
            input.addEventListener('blur', () => {
                if (!input.value) {
                    input.parentElement.classList.remove('focused');
                }
            });
            
            // Real-time validation
            input.addEventListener('input', () => {
                validateInput(input);
            });
        });
        
        form.addEventListener('submit', (e) => {
            let isValid = true;
            
            inputs.forEach(input => {
                if (!validateInput(input)) {
                    isValid = false;
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showNotification('Please check your input and try again.', 'error');
            }
        });
    });
    
    // Password visibility toggle
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        const toggleButton = document.createElement('button');
        toggleButton.type = 'button';
        toggleButton.className = 'password-toggle';
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        
        input.parentElement.appendChild(toggleButton);
        
        toggleButton.addEventListener('click', () => {
            const type = input.getAttribute('type');
            input.setAttribute('type', type === 'password' ? 'text' : 'password');
            toggleButton.innerHTML = type === 'password' ? 
                '<i class="fas fa-eye-slash"></i>' : 
                '<i class="fas fa-eye"></i>';
        });
    });
});

function validateInput(input) {
    const value = input.value.trim();
    let isValid = true;
    const errorDiv = input.parentElement.querySelector('.error-message') || 
                    document.createElement('div');
    errorDiv.className = 'error-message';
    
    switch(input.type) {
        case 'email':
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            isValid = emailRegex.test(value);
            errorDiv.textContent = isValid ? '' : 'Please enter a valid email address';
            break;
            
        case 'password' && input.name != 'update':
            if (input.name === 'password1' || input.name === 'password') {
                isValid = value.length >= 8;
                errorDiv.textContent = isValid
                    ? ''
                    : 'Password must be at least 8 characters long';
            }
            break;
            
        default:
            isValid = value.length >= 0;
            errorDiv.textContent = isValid ? '' : 'This field is required';
    }
    
    if (!errorDiv.parentElement) {
        input.parentElement.appendChild(errorDiv);
    }
    
    input.parentElement.classList.toggle('error', !isValid);
    return isValid;
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}