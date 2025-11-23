<script>
  import { toastStore } from '../stores/toastStore'

  const typeClasses = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warning: 'bg-yellow-500',
    info: 'bg-blue-500'
  }

  const icons = {
    success: 'fas fa-check-circle',
    error: 'fas fa-exclamation-circle',
    warning: 'fas fa-exclamation-triangle',
    info: 'fas fa-info-circle'
  }
</script>

<div class="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
  {#each $toastStore as toast (toast.id)}
    <div
      class="flex items-center space-x-2 px-6 py-3 rounded-lg shadow-lg text-white pointer-events-auto
             transform transition-all duration-300 animate-in slide-in-from-right {typeClasses[toast.type]}"
    >
      <i class="{icons[toast.type]}"></i>
      <span>{toast.message}</span>
    </div>
  {/each}
</div>

<style>
  :global(.animate-in) {
    animation: slideIn 0.3s ease-out;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
</style>
