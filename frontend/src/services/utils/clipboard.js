import { showToast } from '../../stores/toastStore'

export async function copyToClipboard(text, successMessage = 'Copied to clipboard!') {
    try {
        await navigator.clipboard.writeText(text)
        showToast(successMessage, 'success')
    } catch (error) {
        console.error('Failed to copy to clipboard:', error)
        showToast('Failed to copy to clipboard', 'error')
    }
}
