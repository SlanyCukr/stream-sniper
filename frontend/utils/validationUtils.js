/**
 * Email validation helper
 */
export const validateEmail = email => {
    if (!email.trim()) {
        return 'Email is required'
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return 'Please enter a valid email address'
    }
    return null
}

/**
 * Password validation helper
 */
export const validatePasswordChange = passwordData => {
    if (!passwordData.currentPassword) {
        return 'Current password is required'
    }
    if (!passwordData.newPassword) {
        return 'New password is required'
    }
    if (passwordData.newPassword.length < 8) {
        return 'New password must be at least 8 characters long'
    }
    if (!/[A-Za-z]/.test(passwordData.newPassword)) {
        return 'New password must contain at least one letter'
    }
    if (!/[0-9]/.test(passwordData.newPassword)) {
        return 'New password must contain at least one number'
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
        return 'New passwords do not match'
    }
    return null
}
